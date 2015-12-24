#!/usr/bin/env python2.7
# -*- coding: utf-8 -*-

from __future__ import division, absolute_import, print_function, unicode_literals

from copy import deepcopy

from django.db import models


class HideMetaOpts(models.base.ModelBase):
	"""
	A metaclass that hides added attributes from a class' ``Meta``, since
	otherwise Django's fascistic Meta options sanitizer will throw an
	exception. Default values can be set with default_meta_opts. By default
	only opts defined in default_meta_opts will be hidden from Django; if you
	want to hide everything unknown, set hide_unknown_opts to ``True``.
	
	(If you have another mixin that adds to your model's ``Meta``, create a
	``metaclass`` that inherits from both this and the other
	mixin's ``metaclass``.)
	
	"""
	
	default_meta_opts = {}
	hide_unknown_opts = False
	
	def __new__(cls, name, bases, attrs):
		if not [b for b in bases if isinstance(b, HideMetaOpts)]:
			return super(HideMetaOpts, cls).__new__(cls, name, bases, attrs)
		
		else:
			meta_opts = deepcopy(cls.default_meta_opts)
			
			# Deferred fields won't have our model's Meta.
			if 'Meta' in attrs and attrs['Meta'].__module__ != 'django.db.models.query_utils':
				meta = attrs.get('Meta')
			
			else:
				# Meta is at a class level, and could be in any of the bases.
				for base in bases:
					meta = getattr(base, '_meta', None)
					
					if meta:
						break
			
			# If there's no _meta then we're falling back to defaults.
			if meta:
				for opt, value in vars(meta).items():
					if opt not in models.options.DEFAULT_NAMES and (cls.hide_unknown_opts or opt in meta_opts):
						meta_opts[opt] = value
						delattr(meta, opt)
			
			new_class = super(HideMetaOpts, cls).__new__(cls, name, bases, attrs)
			
			if meta:
				for opt in meta_opts:
					setattr(meta, opt, meta_opts[opt])
			
			# We theoretically don't have to set this twice, but just in case.
			for opt in meta_opts:
				setattr(new_class._meta, opt, meta_opts[opt])
			
			return new_class
