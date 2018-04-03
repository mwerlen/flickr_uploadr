#!/usr/bin/env python
# -*- coding:utf-8

from unittest import TestCase
import uploadr

photoSetId = 72157655931047502


class TestUploadr(TestCase):
    def setUp(self):
        self.uploadr = uploadr.Uploadr()

    def test_getPhotoListingFromPhotoSet(self):
        self.uploadr.getPhotoListingFromPhotoSet(photoSetId)
        self.assertGreater(self.uploadr.listings[photoSetId], 501, u'le listing devrait faire plus de 500 éléments')
