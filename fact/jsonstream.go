package fact

import (
	"encoding/json"
	"errors"
	"fmt"
	"io"

	"github.com/chop-dbhi/origins/identity"
	"github.com/sirupsen/logrus"
)

// Auxillary struct to decode a JSON-encoded fact in for parsing.
type auxFact struct {
	Domain    string
	Operation string
	Time      interface{}
	Entity    interface{}
	Attribute interface{}
	Value     interface{}
}

type jsonStreamReader struct {
	reader io.Reader
	buf    []byte
	eof    bool
}

// TODO(bjr): there is a io.ByteReader interface, however it is
// not as general as a general io.Reader.
func (r *jsonStreamReader) next() ([]byte, error) {
	if r.eof {
		return nil, io.EOF
	}

	var (
		n   int
		pos int
		err error
	)

	buflen := len(r.buf)
	b := make([]byte, 1, 1)

	for {
		n, err = r.reader.Read(b)

		// No more bytes available, end of stream.
		if n == 0 || err == io.EOF {
			r.eof = true
			return r.buf[:pos], nil
		}

		if err != nil {
			return nil, err
		}

		if b[0] == '\n' || b[0] == '\r' {
			// There may be multiple newlines or carriage returns in
			// succession, ignore them all.
			if pos != 0 {
				return r.buf[:pos], err
			}
		} else {
			// Double the buffer
			if pos >= buflen {
				buflen = buflen * 2
				nbuf := make([]byte, buflen)

				copy(nbuf, r.buf)

				r.buf = nbuf
			}

			r.buf[pos] = b[0]

			pos += 1
		}
	}
}

func (r *jsonStreamReader) read() (*Fact, error) {
	b, err := r.next()

	// Real error.
	if err != nil {
		return nil, err
	}

	// Decode into an auxillary fact.
	var af auxFact
	err = json.Unmarshal(b, &af)

	if err != nil {
		return nil, err
	}

	f := Fact{}

	// Domain; just a string
	f.Domain = af.Domain

	// Operation
	op, err := ParseOperation(af.Operation)

	if err != nil {
		logrus.Error(err)
		return nil, err
	}

	f.Operation = op

	if af.Time != nil {
		// Time; string or int
		switch x := af.Time.(type) {
		case string:
			t, err := ParseTime(x)

			if err != nil {
				logrus.Error(err)
				return nil, err
			}

			f.Time = t
		case int64:
			// TODO(bjr) should there be a sanity check here?
			f.Time = x
		default:
			err = errors.New(fmt.Sprintf("invalid time value: %v", af.Time))
			return nil, err
		}
	}

	// Entity; string (local) or object
	ident := identity.Ident{}

	switch x := af.Entity.(type) {
	case map[string]interface{}:
		if v, ok := x["domain"]; ok {
			ident.Domain = v.(string)
		}

		if v, ok := x["local"]; ok {
			ident.Local = v.(string)
		}
	case string:
		ident.Local = x
	}

	if ident.Local == "" {
		err = errors.New(fmt.Sprintf("invalid entity format: %v", af.Entity))
		return nil, err
	}

	f.Entity = &ident

	// Attribute; string (local) or object
	ident = identity.Ident{}

	switch x := af.Attribute.(type) {
	case map[string]interface{}:
		if v, ok := x["domain"]; ok {
			ident.Domain = v.(string)
		}

		if v, ok := x["local"]; ok {
			ident.Local = v.(string)
		}
	case string:
		ident.Local = x
	}

	if ident.Local == "" {
		err = errors.New(fmt.Sprintf("invalid attribute format: %v", af.Attribute))
		return nil, err
	}

	f.Attribute = &ident

	// Value; string (local) or object
	ident = identity.Ident{}

	switch x := af.Value.(type) {
	case map[string]interface{}:
		if v, ok := x["domain"]; ok {
			ident.Domain = v.(string)
		}

		if v, ok := x["local"]; ok {
			ident.Local = v.(string)
		}
	case string:
		ident.Local = x
	}

	if ident.Local == "" {
		err = errors.New(fmt.Sprintf("invalid value format: %v", af.Value))
		return nil, err
	}

	f.Value = &ident

	logrus.Debugf("Processed fact %v", &f)

	// Error will be nil or EOF
	return &f, nil
}

// Read satisfies the fact.Reader interface.
func (r *jsonStreamReader) Read(facts Facts) (int, error) {
	var (
		f   *Fact
		err error
		l   = len(facts)
	)

	for i := 0; i < l; i++ {
		f, err = r.read()

		// EOF or error
		if err != nil {
			return i, err
		}

		// Add fact.
		if f != nil {
			facts[i] = f
		}
	}

	return l, nil
}

// JSONStreamReader returns a reader that parsed a stream of newline-delimited
// JSON-encoded facts.
func JSONStreamReader(reader io.Reader) *jsonStreamReader {
	r := jsonStreamReader{
		reader: reader,
		buf:    make([]byte, 200),
	}

	return &r
}

type jsonStreamWriter struct {
	writer io.Writer
}

func (w *jsonStreamWriter) marshal(f *Fact) []byte {
	b, err := json.Marshal(f)

	if err != nil {
		panic(err)
	}

	return b
}

func (w *jsonStreamWriter) Write(facts Facts) (int, error) {
	// Buffer to reduce the number of calls to flush.
	var (
		n   int
		b   []byte
		err error
		nl  = []byte{'\n'}
	)

	for _, f := range facts {
		b = w.marshal(f)

		if _, err = w.writer.Write(b); err != nil {
			return n, err
		}

		if _, err = w.writer.Write(nl); err != nil {
			return n, err
		}

		n += 1
	}

	return n, nil
}

func JSONStreamWriter(writer io.Writer) *jsonStreamWriter {
	return &jsonStreamWriter{
		writer: writer,
	}
}
