import os
from math import acos, degrees, pi
from django import forms
from django.db import models
from django.conf import settings

from modelcluster.fields import ParentalKey

from wagtail.wagtailcore.models import Page, Orderable
from wagtail.wagtailadmin.edit_handlers import FieldPanel, InlinePanel
from wagtail.wagtailimages.edit_handlers import ImageChooserPanel
from wagtail.wagtailsearch import index
from wagtail.wagtaildocs.models import Document
from wagtail.wagtaildocs.edit_handlers import DocumentChooserPanel

class Dxf2VrPage(Page):
    intro = models.CharField(max_length=250, null=True, blank=True,)
    equirectangular_image = models.ForeignKey(
        'wagtailimages.Image', 
        null=True,
        blank=True,
        on_delete = models.SET_NULL, 
        related_name = '+',
        )
    dxf_file = models.ForeignKey(
        'wagtaildocs.Document', 
        null=True, 
        on_delete = models.SET_NULL,
        related_name = '+',
        )

    search_fields = Page.search_fields + [
        index.SearchField('intro'),
        #index.SearchField('body'),
    ]

    content_panels = Page.content_panels + [
        FieldPanel('intro'),
        DocumentChooserPanel('dxf_file'),
        ImageChooserPanel('equirectangular_image'),
        InlinePanel('material_images', label="Material Image Gallery",),
    ]

    def extract_blocks(self):
        path_to_dxf = os.path.join(settings.MEDIA_ROOT, 'documents', self.dxf_file.filename)
        dxf_f = open(path_to_dxf, encoding = 'utf-8')
        output = {}
        flag = False
        x = 0
        value = 'dummy'
        while value !='ENTITIES':
            key = dxf_f.readline().strip()
            value = dxf_f.readline().strip()
        while value !='ENDSEC':
            key = dxf_f.readline().strip()
            value = dxf_f.readline().strip()
            if flag == True:
                if key == '20':#mirror Y position
                    value = -float(value)
                elif key == '210':#rotation around X
                    value = degrees(pi/2-acos(float(value)))
                elif key == '220':#rotation around Y
                    value = -degrees(pi/2-acos(float(value)))
                temp[key] = value
            if key == '0':
                if flag == True:
                    output[x] = temp
                    flag = False
                if value == 'INSERT':
                    temp = {'41': 1, '42': 1, '43': 1, '50': 0, '210': 0, '220': 0}#default values
                    flag = True
                    x += 1
                #here other ifs for other kind of entities
        dxf_f.close()
        return output

    def extract_3Dfaces(self):
        path_to_dxf = os.path.join(settings.MEDIA_ROOT, 'documents', self.dxf_file.filename)
        dxf_f = open(path_to_dxf, encoding = 'utf-8')
        output = {}
        flag = False
        x = 0
        value = 'dummy'
        while value !='ENTITIES':
            key = dxf_f.readline().strip()
            value = dxf_f.readline().strip()
        while value !='ENDSEC':
            key = dxf_f.readline().strip()
            value = dxf_f.readline().strip()
            if flag == True:
                if key == '20' or key == '21' or key == '22' or key == '23':#mirror Y position
                    value = -float(value)
                temp[key] = value
            if key == '0':
                if flag == True:
                    output[x] = temp
                    flag = False
                if value == '3DFACE':
                    temp = {}#default values
                    flag = True
                    x += 1
                #here other ifs for other kind of entities
        dxf_f.close()
        return output

class Dxf2VrPageMaterialImage(Orderable):
    page = ParentalKey(Dxf2VrPage, related_name='material_images')
    image = models.ForeignKey(
        'wagtailimages.Image', 
        null=True,
        blank=True,
        on_delete = models.SET_NULL, 
        related_name = '+',
    )
    layer = models.CharField(max_length=250, default="0",)
    color = models.CharField(max_length=250, default="white",)

    panels = [
        FieldPanel('layer'),
        ImageChooserPanel('image'),
        FieldPanel('color'),
]