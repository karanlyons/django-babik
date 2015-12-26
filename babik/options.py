#!/usr/bin/env python2.7
# -*- coding: utf-8 -*-

from __future__ import division, absolute_import, print_function, unicode_literals

from django.core.exceptions import FieldDoesNotExist
from django.db import models
from django.db.models.options import make_immutable_fields_list, Options
from .fields import BabikAttrsField, BabikTypeField


class DynamicOptions(Options):
	def _patch(self, instance=None, model=None, meta=None):
		'''
		Shallow copies all the prexisting attributes of the instance's original
		Options, and saves a reference back to the instance. Since we shallow
		copy all that we can, the overheard of a per instance as opposed to per
		class Options is minimized.
		
		'''
		
		if meta:
			self.__dict__.update({k: v for k, v in meta.__dict__.iteritems() if k != 'virtual_fields'})
			self._virtual_fields = meta.virtual_fields
		
		elif instance:
			self.__dict__.update({k: v for k, v in instance.__class__._meta.__dict__.iteritems() if k != 'virtual_fields'})
			self._virtual_fields = instance.__class__._meta.virtual_fields
		
		elif model:
			self.__dict__.update({k: v for k, v in model._meta.__dict__.iteritems() if k != 'virtual_fields'})
			self._virtual_fields = model._meta.virtual_fields
		
		self.instance = instance if instance else getattr(self, 'instance', None)
		self.attrs_field = getattr(self, 'attrs_field', None)
		self.type_field = getattr(self, 'type_field', None)
		
		if not(self.attrs_field and self.type_field):
			for field in super(DynamicOptions, self).fields:
				self._bind_babkik_fields(field)
				
				if self.attrs_field and self.type_field:
					break
	
	@property
	def type(self):
		if self.instance and self.attrs_field and self.attrs_field.type_key:
			return self.attrs_field.types.get(
				models.Model.__getattribute__(self.instance, '__dict__').get(self.attrs_field.attname, {}).get(self.attrs_field.type_key, None)
			)
		
		else:
			return None
	
	def add_field(self, field, virtual=False):
		if virtual:
			self._virtual_fields.append(field)
		
		else:
			super(DynamicOptions, self).add_field(field, virtual)
			self._bind_babkik_fields(field)
	
	def _bind_babkik_fields(self, field):
		if isinstance(field, BabikAttrsField):
			self.attrs_field = field
		
		elif isinstance(field, BabikTypeField):
			self.type_field = field
	
	@property
	def fields(self):
		instance_type = self.type
		
		if instance_type:
			return make_immutable_fields_list('fields', super(DynamicOptions, self).fields + self.attrs_field.type._meta.fields)
		
		else:
			return super(DynamicOptions, self).fields
	
	@property
	def virtual_fields(self):
		'''
		Rather than patch every field's contribute_to_class method to assign
		itself as virtual (requiring that ModelType have its own special
		Options as well or that users use factory build Babik version of every
		possible field), we just take all the fields in a ModelType and say
		they're virtual, since they always will be.
		
		'''
		
		instance_type = self.type
		
		if instance_type:
			return self._virtual_fields + list(self.type._meta.fields)
		
		else:
			return self._virtual_fields
	
	def get_field(self, field_name, many_to_many=None):
		field = None
		instance_type = self.type
		
		if instance_type:
			try:
				field = instance_type._meta.get_field(field_name, many_to_many)
			
			except FieldDoesNotExist:
				pass
		
		# If we don't have an instance, we can't know its type, so we can't
		# return the correct field.
		if not field:
			# Try pulling out a standard field from the model.
			try:
				return super(DynamicOptions, self).get_field(field_name, many_to_many)
			
			except FieldDoesNotExist:
				# There's no real field and we don't have an instance, so if
				# this is a field name that *could* map to an eventual virtual
				# field let's just lie again and hope we don't have to
				# apologize later.
				if not instance_type and self.attrs_field and field_name in self.attrs_field.potential_virtual_field_names:
					field = models.Field()
					
					# Set some defaults for the field so it looks nice, and also tell
					# Django that this field is not backed by a database column.
					field.set_attributes_from_name(field_name)
					field.concrete = False
					field.column = None
					field.db_column = None
					field.db_index = False
				
				else:
					raise
		
		field.model = self.model
		
		return field
