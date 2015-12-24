#!/usr/bin/env python2.7
# -*- coding: utf-8 -*-

from __future__ import division, absolute_import, print_function, unicode_literals

from django.db import models


class ModelTypeMeta(models.base.ModelBase):
	def __new__(cls, name, bases, attrs):
		attrs['Meta'].abstract = True
		
		new_class = super(ModelTypeMeta, cls).__new__(cls, name, bases, attrs)
		
		for name, value in attrs.iteritems():
			if isinstance(value, models.Field):
				value.set_attributes_from_name(name)
				value.concrete = False
				value.column = None
		
		return new_class


class ModelType(models.Model):
	__metaclass__ = ModelTypeMeta
	
	class Meta:
		abstract = True
