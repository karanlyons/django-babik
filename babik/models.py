#!/usr/bin/env python2.7
# -*- coding: utf-8 -*-

from __future__ import division, absolute_import, print_function, unicode_literals

from django.db import models
from django.core.exceptions import ValidationError

from .options import DynamicOptions
from .utils import HideMetaOpts


class DynamicModelMeta(HideMetaOpts):
	default_meta_opts = {
		'attrs_field': None,
		'type_field': None,
		'types': None,
	}


class DynamicModel(models.Model):
	__metaclass__ = DynamicModelMeta
	
	class Meta:
		abstract = True
	
	def __init__(self, *args, **kwargs):
		super(DynamicModel, self).__init__(*args, **kwargs)
		self._patch_meta()
	
	@classmethod
	def from_db(cls, db, field_names, values):
		instance = super(DynamicModel, cls).from_db(db, field_names, values)
		instance._patch_meta()
		
		return instance
	
	def _patch_meta(self):
		'''
		Patches the model's Meta so that we can return fields that don't really
		exist. To do so we need to swap in our own get_field function and also
		give Meta a link back to the parent instance. The latter part is tricky
		as Meta exists at a class level, not an object level, so we create a
		shallow copy of Meta at an object level to add our needed attribute
		with as little overhead as possible.
		
		'''
		
		if not isinstance(self._meta, DynamicOptions) or getattr(self._meta, 'instance', None) is not self:
			# We don't want to call __init__ as we're going to copy all the
			# attributes over. So we create an empty class, instantiate *that*
			# and then swap out that new object's class for DynamicOptions.
			patched_meta = type(b'DynamicOptions', (), {})()
			patched_meta.__class__ = DynamicOptions
			patched_meta._patch(self)
			self._meta = patched_meta
	
	def save(self, *args, **kwargs):
		if self.type and self.type in self._meta.types:
			errors = {}
			
			for field in self._meta.virtual_fields:
				if hasattr(self._meta.types[self.type], field.attname):
					raw_value = getattr(self, field.attname)
					if field.blank and raw_value in field.empty_values:
						continue
					
					try:
						setattr(self, field.attname, field.clean(raw_value, self))
					
					except ValidationError as error:
						errors[field.name] = error.error_list
				
				if errors:
					raise ValidationError(errors)
		
		super(DynamicModel, self).save(*args, **kwargs)
	
	def __getattribute__(self, name):
		dct = super(DynamicModel, self).__getattribute__('__dict__')
		meta = super(DynamicModel, self).__getattribute__('_meta')
		
		if (
			name[0] != '_' and
			getattr(meta, 'type_field', None) is not None
			and dct.get(meta.type_field, None) is not None
			and meta.attrs_field in dct
			and dct[meta.type_field] in meta.types
			and hasattr(meta.types[dct[meta.type_field]], name)
		):
			return super(DynamicModel, self).__getattribute__(meta.attrs_field).get(name)
		
		else:
			return super(DynamicModel, self).__getattribute__(name)
	
	def __setattr__(self, name, value):
		if (
			getattr(self, self._meta.type_field, None) is not None
			and hasattr(self, self._meta.attrs_field)
			and getattr(self, self._meta.type_field) in self._meta.types
			and hasattr(self._meta.types[getattr(self, self._meta.type_field)], name)
		):
			print(name, value)
			getattr(self, self._meta.attrs_field)[name] = value
		
		else:
			super(DynamicModel, self).__setattr__(name, value)
	
	def __delattr__(self, name):
		if (
			getattr(self, self._meta.type_field, None) is not None
			and hasattr(self, self._meta.attrs_field)
			and getattr(self, self._meta.type_field) in self._meta.types
			and hasattr(self._meta.types[getattr(self, self._meta.type_field)], name)
		):
			del(getattr(self, self._meta.attrs_field)[name])
		
		else:
			super(DynamicModel, self).__delattr__(name)
