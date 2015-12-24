#!/usr/bin/env python2.7
# -*- coding: utf-8 -*-

from __future__ import division, absolute_import, print_function, unicode_literals

from django.db import models


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


for field in (
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
	locals()['Babik%s' % field.__name__] = type(b'Babik%s' % field.__name__, (BabikField, field), {})
