#!/usr/bin/env python2.7
# -*- coding: utf-8 -*-

from __future__ import division, absolute_import, print_function, unicode_literals

from django.db import models

from .options import DynamicOptions


class DynamicModelMeta(models.base.ModelBase):
	def __new__(cls, name, bases, attrs):
		new_class = super(DynamicModelMeta, cls).__new__(cls, name, bases, attrs)
		
		patched_meta = type(b'DynamicOptions', (), {})()
		patched_meta.__class__ = DynamicOptions
		patched_meta._patch(model=new_class, meta=new_class._meta)
		
		new_class._meta = patched_meta
		
		return new_class


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
			patched_meta._patch(instance=self)
			self._meta = patched_meta
	
	def __getattribute__(self, name):
		meta = super(DynamicModel, self).__getattribute__('_meta')
		model_type = getattr(meta, 'type', None)
		
		if model_type and name in model_type._meta._forward_fields_map:
			return model_type._meta._forward_fields_map[name].to_python(super(DynamicModel, self).__getattribute__(meta.attrs_field.attname).get(name))
		
		return super(DynamicModel, self).__getattribute__(name)
	
	def __setattr__(self, name, value):
		model_type = getattr(self._meta, 'type', None)
		
		if model_type and name in model_type._meta._forward_fields_map:
			value = model_type._meta._forward_fields_map[name].to_python(value)
			
			getattr(self, self._meta.attrs_field.attname)[name] = value
		
		else:
			super(DynamicModel, self).__setattr__(name, value)
		
		if (
			self._meta.type_field
			and name == self._meta.type_field.attname
			and self._meta.attrs_field
			and hasattr(self, self._meta.attrs_field.attname)
		):
			getattr(self, self._meta.attrs_field.attname)[self._meta.attrs_field.type_key] = value
