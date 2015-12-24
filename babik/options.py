#!/usr/bin/env python2.7
# -*- coding: utf-8 -*-

from __future__ import division, absolute_import, print_function, unicode_literals

from django.core.exceptions import FieldDoesNotExist
from django.db import models
from django.db.models.options import make_immutable_fields_list, Options


class DynamicOptions(Options):
	def _patch(self, instance):
		self.__dict__.update({k: v for k, v in instance.__class__._meta.__dict__.iteritems() if k != 'virtual_fields'})
		self.instance = instance
		self._virtual_fields = instance.__class__._meta.virtual_fields
	
	def add_field(self, field, virtual=False):
		if virtual:
			self._virtual_fields.append(field)
		
		else:
			super(DynamicOptions, self).add_field(field, virtual)
	
	@property
	def fields(self):
		instance_type = getattr(self.instance, self.type_field, None)
		
		if instance_type in self.types:
			return make_immutable_fields_list(
				'fields',
				super(DynamicOptions, self).fields + tuple(
					field for field in vars(self.types[instance_type]).itervalues()
					if isinstance(field, models.Field)
				)
			)
		
		else:
			return super(DynamicOptions, self).fields
	
	@property
	def virtual_fields(self):
		instance_type = getattr(self.instance, self.type_field, None)
		
		if instance_type in self.types:
			return self._virtual_fields + [field for field in vars(self.types[instance_type]).itervalues() if isinstance(field, models.Field)]
		
		else:
			return self._virtual_fields
	
	def get_field(self, field_name, many_to_many=None):
		field = None
		model_type = getattr(self.instance, self.type_field, None)
		
		if self.instance:
			if model_type is not None and model_type in self.types and hasattr(self.types[model_type], field_name):
				field = getattr(self.types[model_type], field_name)
			
			# This instance hasn't been commited to the database yet, so it
			# could be fresh and empty. In this case lets just lie and hope
			# that the field_name being requested will *eventually* exist.
			elif self.instance._state.db is None and field_name not in self._forward_fields_map:
				field = models.Field()
		
		# If we don't have an instance, we can't know its type, so we can't
		# return the correct field.
		if not field:
			# Try pulling out a standard field from the model.
			try:
				return super(DynamicOptions, self).get_field(field_name, many_to_many)
			
			except FieldDoesNotExist:
				# There's no real field and we don't have an instance, so
				# let's just lie again and hope we don't have to apologize
				# later.
				if not self.instance:
					field = models.Field()
				
				else:
					raise
		
		# Set some defaults for the field so it looks nice, and also tell
		# Django that this field is not backed by a database column.
		if type(field) is models.Field:
			field.set_attributes_from_name(field_name)
			field.concrete = False
			field.column = None
		
		field.model = self.instance
		
		return field
