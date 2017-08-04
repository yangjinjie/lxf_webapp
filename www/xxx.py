#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 24/07/2017 2:46 PM
# @Author  : yang

import re


cmd = 'delete * where fasfs'
r = re.match("(?P<start>select |delete |insert )(?P<line>\S* )(?P<where>where )(?P<condition>\S*)",cmd)

print(r.group('start'))