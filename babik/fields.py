#!/usr/bin/env python2.7
# -*- coding: utf-8 -*-

from __future__ import division, absolute_import, print_function, unicode_literals

import simplejson as json
from psycopg2.extras import Json, register_default_jsonb

from django.forms.widgets import Select
from django.contrib.postgres.fields import JSONField
from django.core import exceptions
from django.db import models


class BabikTypeField(models.Field):
	widget = Select
	
	def __init__(self, *args, **kwargs):
		super(BabikTypeField, self).__init__(*args, **kwargs)
		
		flat = []
		
		for choice, value in self.choices:
			if isinstance(value, (list, tuple)):
				flat.extend(value)
			
			else:
				flat.append((choice, value))
		
		self.choice_db_to_verbose = dict(flat)
		self.choice_verbose_to_db = {v: k for k, v in flat}
	
	def contribute_to_class(self, cls, name):
		self.model = cls
		
		for field in self.model._meta.fields:
			if isinstance(field, BabikAttrsField):
				if field.type_key is None:
					field.type_key = self.attname
					
					break
		
		super(BabikTypeField, self).contribute_to_class(cls, name)
	
	@property
	def flatchoices(self):
		flat = []
		
		for choice, value in self.choices:
			if isinstance(value, (list, tuple)):
				for optgroup_choice, optgroup_value in value:
					flat.extend(((optgroup_choice, optgroup_value), (optgroup_value, optgroup_value)))
			
			else:
				flat.extend(((choice, value), (value, value)))
		
		return flat
	
	def from_db_value(self, value, expression, connection, context):
		if not isinstance(value, basestring):
			value = self.choice_db_to_verbose.get(value, value)
		
		return value
	
	def get_prep_value(self, value):
		if not isinstance(value, (int, long)):
			value = self.choice_verbose_to_db.get(value, value)
		
		return value
	
	def get_db_prep_value(self, value, connection, prepared=False):
		if not isinstance(value, (int, long)):
			value = self.choice_verbose_to_db.get(value, value)
		
		return super(BabikTypeField, self).get_db_prep_value(value, connection, prepared)
	
	def get_internal_type(self):
		return 'IntegerField'
	
	def to_python(self, value):
		if not isinstance(value, basestring):
			value = self.choice_db_to_verbose.get(value, value)
		
		return value
	
	def value_to_string(self, obj):
		if not isinstance(obj, (int, long)):
			obj = self.choice_verbose_to_db.get(obj, obj)
		
		return obj
	
	def validate(self, value, model_instace):
		if not isinstance(value, (int, long)):
			value = self.choice_verbose_to_db.get(value, value)
		
		return super(BabikTypeField, self).validate(value, model_instace)
	
	def run_validators(self, value):
		if not isinstance(value, (int, long)):
			value = self.choice_verbose_to_db.get(value, value)
		
		super(BabikTypeField, self).run_validators(value)


class DecimalSafeJsonEncoder(Json):
	def dumps(self, obj):
		return json.dumps(obj, use_decimal=True)


class BabikAttrsField(JSONField):
	def __init__(self, types, *args, **kwargs):
		self.types = types
		self.type_key = kwargs.pop('type_key', 'type')
		
		super(BabikAttrsField, self).__init__(*args, **kwargs)
	
	def contribute_to_class(self, cls, name):
		self.model = cls
		
		if self.type_key is None:
			for field in self.model._meta.fields:
				if isinstance(field, BabikTypeField):
					self.type_key = field.attname
					
					break
		
		super(BabikAttrsField, self).contribute_to_class(cls, name)
	
	def deconstruct(self):
		name, path, args, kwargs = super(BabikField, self).deconstruct()
		
		if self.type_key:
			kwargs['type_key'] = self.type_key
		
		if self.types:
			kwargs['types'] = self.types
		
		return name, path, args, kwargs
	
	def get_prep_value(self, value):
		if value is not None:
			return DecimalSafeJsonEncoder(value)
		
		else:
			return value
	
	def validate(self, value, model_instance):
		super(BabikAttrsField, self).validate(value, model_instance)
		
		try:
			json.dumps(value)
		
		except TypeError:
			raise exceptions.ValidationError(
				self.error_messages['invalid'],
				code='invalid',
				params={'value': value},
			)
	
	def get_db_prep_save(self, value, connection):
		model_type = None
		
		if self.type_key in value:
			model_type = self.types.get(value[self.type_key], None)
			
			if model_type:
				errors = {}
				
				for field in model_type._meta.fields:
					raw_value = value[field.attname]
					
					if field.blank and raw_value in field.empty_values:
						continue
					
					try:
						value[field.attname] = field.get_db_prep_save(raw_value, connection)
					
					except exceptions.ValidationError as error:
						errors[field.name] = error.error_list
				
				if errors:
					raise exceptions.ValidationError(errors)
		
		if model_type is None:
			raise exceptions.ValidationError(
				'No type specified for model',
				code='invalid',
			)
		
		return super(BabikAttrsField, self).get_db_prep_save(value, connection)


def decimal_safe_json_decoder(data):
	return json.loads(data, use_decimal=True)


register_default_jsonb(globally=True, loads=decimal_safe_json_decoder)


class BabikField(models.Field):
	auto_created = False
	concrete = False
	editable = False
	hidden = False
	
	is_relation = False
	many_to_many = False
	many_to_one = False
	one_to_many = False
	one_to_one = False
	related_model = None
	remote_field = None
	
	def __init__(self, attrs_field, *args, **kwargs):
		self.attrs_field = attrs_field
		self.attr_name = kwargs.pop('attr_name', None)
		
		super(BabikField, self).__init__(*args, **kwargs)
		
		self.concrete = False
		self.column = None
		self.db_column = None
		self.db_index = False
	
	def contribute_to_class(self, cls, name, virtual_only=False):
		self.set_attributes_from_name(name)
		self.model = cls
		cls._meta.add_field(self, virtual=True)
		setattr(cls, self.attname, self)
	
	def get_attname_column(self):
		return self.get_attname(), None
	
	@property
	def description(self):
		return 'BabikField of %s, underwritten by %s' % (super(BabikField, self).description, self.attrs_field)
	
	def deconstruct(self):
		name, path, args, kwargs = super(BabikField, self).deconstruct()
		
		kwargs['attrs_field'] = self.attrs_field
		
		if self.attr_name:
			kwargs['attr_name'] = self.attr_name
		
		return name, path, args, kwargs
	
	def __get__(self, instance, instance_type=None):
		if instance is None:
			return self
		
		try:
			return getattr(instance, self.attrs_field)[self.attr_name if self.attr_name else self.attname]
		
		except AttributeError:
			raise AttributeError('Underwritten field %s has not been loaded' % self.attrs_field)
	
	def __set__(self, instance, value):
		value = super(BabikField, self).clean(value, instance)
		
		try:
			getattr(instance, self.attrs_field)[self.attr_name if self.attr_name else self.attname] = value
		
		except AttributeError:
			raise AttributeError('Underwritten field %s has not been loaded' % self.attrs_field)


def babik_field_factory(base_field, name=None):
	return type(name if name else b'Babik%s' % base_field.__name__, (BabikField, base_field), {})


for base_field in (
	models.BigIntegerField,
	models.BooleanField,
	models.CharField,
	models.CommaSeparatedIntegerField,
	models.DecimalField,
	models.EmailField,
	models.FilePathField,
	models.FloatField,
	models.IntegerField,
	models.GenericIPAddressField,
	models.NullBooleanField,
	models.PositiveIntegerField,
	models.PositiveSmallIntegerField,
	models.SlugField,
	models.SmallIntegerField,
	models.TextField,
	models.URLField,
):
	locals()['Babik%s' % base_field.__name__] = babik_field_factory(base_field)
