# Copyright 2017-2019 TensorHub, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import absolute_import
from __future__ import division

import fnmatch
import glob
import os
import re
import shutil

import six

from guild import util

class FileSelect(object):

    def __init__(self, root, rules):
        self.root = root
        self.rules = rules

    def select_file(self, src_root, relpath):
        last_rule_result = None
        for rule in self.rules:
            if rule.type == "dir":
                continue
            rule_result = rule.test(src_root, relpath)
            if rule_result is not None:
                last_rule_result = rule_result
        return last_rule_result is True

    def prune_dirs(self, src_root, relpath, dirs):
        for name in list(dirs):
            last_rule_result = None
            for rule in self.rules:
                if rule.type != "dir":
                    continue
                rule_result = rule.test(src_root, os.path.join(relpath, name))
                if rule_result is not None:
                    last_rule_result = rule_result
            if last_rule_result is False:
                dirs.remove(name)

class FileSelectRule(object):

    def __init__(
            self,
            result,
            patterns,
            regex=False,
            type=None,
            sentinel=None,
            size_gt=None,
            size_lt=None):
        self.result = result
        if isinstance(patterns, six.string_types):
            patterns = [patterns]
        self.patterns = patterns
        self.regex = regex
        self._patterns_match = self._patterns_match_f(patterns, regex)
        self.type = self._validate_type(type)
        self.sentinel = sentinel
        self.size_gt = size_gt
        self.size_lt = size_lt

    @staticmethod
    def _patterns_match_f(patterns, regex):
        if regex:
            compiled = [re.compile(p) for p in patterns]
            return lambda path: any((p.match(path) for p in compiled))
        else:
            match = fnmatch.fnmatch
            return lambda path: any((match(path, p) for p in patterns))

    @staticmethod
    def _validate_type(type):
        valid = ("text", "binary", "dir")
        if type is not None and type not in valid:
            raise ValueError(
                "invalid value for type %r: expected one of %s"
                % (type, ", ".join(valid)))
        return type

    def test(self, src_root, relpath):
        fullpath = os.path.join(src_root, relpath)
        tests = [
            lambda: self._test_patterns(relpath),
            lambda: self._test_type(fullpath),
            lambda: self._test_size(fullpath),
        ]
        for test in tests:
            if not test():
                return None
        return self.result

    def _test_patterns(self, path):
        return self._patterns_match(path)

    def _test_type(self, path):
        if self.type is None:
            return True
        if self.type == "text":
            return self._test_text_file(path)
        elif self.type == "binary":
            return self._test_binary_file(path)
        elif self.type == "dir":
            return self._test_dir(path)
        else:
            assert False, self.type

    @staticmethod
    def _test_text_file(path):
        return util.is_text_file(path)

    @staticmethod
    def _test_binary_file(path):
        return not util.is_text_file(path)

    def _test_dir(self, path):
        if not os.path.isdir(path):
            return False
        if self.sentinel:
            return glob.glob(os.path.join(path, self.sentinel))
        return True

    def _test_size(self, path):
        if self.size_gt is None and self.size_lt is None:
            return True
        size = os.path.getsize(path)
        if self.size_gt and size > self.size_gt:
            return True
        if self.size_lt and size < self.size_lt:
            return True
        return False

def include(patterns, **kw):
    return FileSelectRule(True, patterns, **kw)

def exclude(patterns, **kw):
    return FileSelectRule(False, patterns, **kw)

class DebugCallback(object):
    pass

class FileCopyHandler(object):

    def __init__(self, src_root, dest_root, debug_cb=None, error_handler=None):
        self.src_root = src_root
        self.dest_root = dest_root
        self.debug_cb = debug_cb
        self.error_handler = error_handler

    def copy(self, path):
        src = os.path.join(self.src_root, path)
        dest = os.path.join(self.dest_root, path)
        util.ensure_dir(os.path.dirname(dest))
        self._try_copy_file(src, dest)

    def _try_copy_file(self, src, dest):
        try:
            shutil.copyfile(src, dest)
        except IOError as e:
            if e.errno != 2: # Ignore file not exists
                if not self.error_handler:
                    raise
                self.error_handler(e)
        except OSError as e:
            if not self.error_handler:
                raise
            self.error_handler(e)

    def ignore(self, path):
        pass

def copytree(dest, select, root_start=None, followlinks=True, debug_cb=None):
    """Copies files to dest for a FileSelect.

    root_start is an optional location from which select.root, if
    relative, starts. Defaults to os.curdir.

    If followlinks is True (the default), follows linked directories
    when copying the tree.

    If debug_cb is specified, does not copy files but instead invokes
    debub_cb methods as it evaluates source files to copy. debug_cb
    must implement the DebugCallback interface.
    """
    src = _copytree_src(root_start, select)
    handler = FileCopyHandler(src, dest, debug_cb)
    for root, dirs, files in os.walk(src, followlinks=followlinks):
        relroot = _relpath(root, src)
        select.prune_dirs(src, relroot, dirs)
        for name in files:
            relpath = os.path.join(relroot, name)
            if select.select_file(src, relpath):
                handler.copy(relpath)
            else:
                handler.ignore(relpath)

def _copytree_src(root_start, select):
    root_start = root_start or os.curdir
    if select.root:
        return os.path.join(root_start, select.root)
    return root_start

def _relpath(path, start):
    if path == start:
        return ""
    return os.path.relpath(path, start)
