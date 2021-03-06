// Code generated by protoc-gen-go.
// source: fact/fact.proto
// DO NOT EDIT!

/*
Package fact is a generated protocol buffer package.

It is generated from these files:
	fact/fact.proto

It has these top-level messages:
	ProtoFact
*/
package fact

import proto "github.com/golang/protobuf/proto"
import math "math"

// Reference imports to suppress errors if they are not otherwise used.
var _ = proto.Marshal
var _ = math.Inf

type ProtoFact struct {
	Domain           *string `protobuf:"bytes,1,opt" json:"Domain,omitempty"`
	Operation        *string `protobuf:"bytes,2,req" json:"Operation,omitempty"`
	Time             *int64  `protobuf:"varint,3,req" json:"Time,omitempty"`
	EntityDomain     *string `protobuf:"bytes,4,req" json:"EntityDomain,omitempty"`
	Entity           *string `protobuf:"bytes,5,req" json:"Entity,omitempty"`
	AttributeDomain  *string `protobuf:"bytes,6,req" json:"AttributeDomain,omitempty"`
	Attribute        *string `protobuf:"bytes,7,req" json:"Attribute,omitempty"`
	ValueDomain      *string `protobuf:"bytes,8,req" json:"ValueDomain,omitempty"`
	Value            *string `protobuf:"bytes,9,req" json:"Value,omitempty"`
	Transaction      *string `protobuf:"bytes,10,opt" json:"Transaction,omitempty"`
	Inferred         *bool   `protobuf:"varint,11,req" json:"Inferred,omitempty"`
	XXX_unrecognized []byte  `json:"-"`
}

func (m *ProtoFact) Reset()         { *m = ProtoFact{} }
func (m *ProtoFact) String() string { return proto.CompactTextString(m) }
func (*ProtoFact) ProtoMessage()    {}

func (m *ProtoFact) GetDomain() string {
	if m != nil && m.Domain != nil {
		return *m.Domain
	}
	return ""
}

func (m *ProtoFact) GetOperation() string {
	if m != nil && m.Operation != nil {
		return *m.Operation
	}
	return ""
}

func (m *ProtoFact) GetTime() int64 {
	if m != nil && m.Time != nil {
		return *m.Time
	}
	return 0
}

func (m *ProtoFact) GetEntityDomain() string {
	if m != nil && m.EntityDomain != nil {
		return *m.EntityDomain
	}
	return ""
}

func (m *ProtoFact) GetEntity() string {
	if m != nil && m.Entity != nil {
		return *m.Entity
	}
	return ""
}

func (m *ProtoFact) GetAttributeDomain() string {
	if m != nil && m.AttributeDomain != nil {
		return *m.AttributeDomain
	}
	return ""
}

func (m *ProtoFact) GetAttribute() string {
	if m != nil && m.Attribute != nil {
		return *m.Attribute
	}
	return ""
}

func (m *ProtoFact) GetValueDomain() string {
	if m != nil && m.ValueDomain != nil {
		return *m.ValueDomain
	}
	return ""
}

func (m *ProtoFact) GetValue() string {
	if m != nil && m.Value != nil {
		return *m.Value
	}
	return ""
}

func (m *ProtoFact) GetTransaction() string {
	if m != nil && m.Transaction != nil {
		return *m.Transaction
	}
	return ""
}

func (m *ProtoFact) GetInferred() bool {
	if m != nil && m.Inferred != nil {
		return *m.Inferred
	}
	return false
}

func init() {
}
