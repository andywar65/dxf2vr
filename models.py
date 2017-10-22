import os
from math import acos, degrees, pi, sqrt, pow, fabs
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
                if key == '210':#rotation around OCS x
                    Az_1 = float(value)
                    P_x = float(temp['10'])
                    #value = degrees(pi/2-acos(float(value)))
                elif key == '220':#rotation around OCS y
                    Az_2 = float(value)
                    P_y = float(temp['20'])
                    #value = -degrees(pi/2-acos(float(value)))
                elif key == '230':#arbitrary axis algorithm
                    Az_3 = float(value)
                    P_z = float(temp['30'])
                    #see if OCS z axis is close to world Z axis
                    if fabs(Az_1) < (1/64) and fabs(Az_2) < (1/64):
                        W = ('dummy', 0, 1, 0)
                    else:
                        W = ('dummy', 0, 0, 1)
                    #cross product for OCS x axis, normalized
                    Ax_1 = W[2]*Az_3-W[3]*Az_2
                    Ax_2 = W[3]*Az_1-W[1]*Az_3
                    Ax_3 = W[1]*Az_2-W[2]*Az_1
                    Norm = sqrt(pow(Ax_1, 2)+pow(Ax_2, 2)+pow(Ax_3, 2))
                    Ax_1 = Ax_1/Norm
                    Ax_2 = Ax_2/Norm
                    Ax_3 = Ax_3/Norm
                    #cross product for OCS y axis, normalized
                    Ay_1 = Az_2*Ax_3-Az_3*Ax_2
                    Ay_2 = Az_3*Ax_1-Az_1*Ax_3
                    Ay_3 = Az_1*Ax_2-Az_2*Ax_1
                    Norm = sqrt(pow(Ay_1, 2)+pow(Ay_2, 2)+pow(Ay_3, 2))
                    Ay_1 = Ay_1/Norm
                    Ay_2 = Ay_2/Norm
                    Ay_3 = Ay_3/Norm
                    #world coordinates from OCS
                    temp['10'] = P_x*Ax_1+P_y*Ay_1+P_z*Az_1
                    temp['20'] = P_x*Ax_2+P_y*Ay_2+P_z*Az_2
                    temp['30'] = P_x*Ax_3+P_y*Ay_3+P_z*Az_3
                temp[key] = value
            if key == '0':
                if flag == True:
                    temp['20'] = - float(temp['20'])#mirror Y position
                    temp['30'] = float(temp['30']) + float(temp['43'])/2#correct Z position
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
                    if temp['12']!=temp['13'] or temp['22']!=temp['23'] or temp['32']!=temp['33']:
                        temp2 = temp.copy()
                        temp2['11']=temp['12']; temp2['21']=temp['22']; temp2['31']=temp['32']
                        temp2['12']=temp['13']; temp2['22']=temp['23']; temp2['32']=temp['33']
                        x += 1
                        output[x] = temp2
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