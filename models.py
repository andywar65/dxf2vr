import os
from math import radians, sin, cos, acos, degrees, pi, sqrt, pow, fabs
from django import forms
from django.db import models
from django.conf import settings

from modelcluster.fields import ParentalKey

from wagtail.wagtailcore.models import Page, Orderable
from wagtail.wagtailadmin.edit_handlers import FieldPanel, InlinePanel, MultiFieldPanel
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
    shadows = models.BooleanField(default=False)
    fly_camera = models.BooleanField(default=False)
    double_face = models.BooleanField(default=False)

    search_fields = Page.search_fields + [
        index.SearchField('intro'),
        #index.SearchField('body'),
    ]

    content_panels = Page.content_panels + [
        FieldPanel('intro'),
        DocumentChooserPanel('dxf_file'),
        ImageChooserPanel('equirectangular_image'),
        MultiFieldPanel([
            FieldPanel('shadows'),
            FieldPanel('fly_camera'),
            FieldPanel('double_face'),
        ], heading="Visual settings"),
        InlinePanel('material_images', label="Material Image Gallery",),
    ]

    def extract_dxf(self):
        path_to_dxf = os.path.join(settings.MEDIA_ROOT, 'documents', self.dxf_file.filename)
        dxf_f = open(path_to_dxf, encoding = 'utf-8')
        material_gallery=self.material_images.all()
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
            if flag == 'face':
                if key == '8':#layer name
                    temp[key] = value
                elif key == '10' or key == '11' or key == '12' or key == '13':#X position
                    temp[key] = value
                elif key == '20' or key == '21' or key == '22' or key == '23':#mirror Y position
                    value = -float(value)
                    temp[key] = value
                elif key == '30' or key == '31' or key == '32' or key == '33':#Z position
                    temp[key] = value
            elif flag == 'block':
                if key == '2' or key == '8':#block name and layer name
                    temp[key] = value
                elif key == '10' or key == '30':#X Z position
                    temp[key] = value
                elif key == '20':#Y position, mirrored
                    temp[key] = -float(value)
                elif key == '50':#Z rotation
                    temp[key] = value
                elif key == '41' or key == '42' or key == '43':#scale values
                    temp[key] = value
                elif key == '210':#X of OCS unitary vector
                    Az_1 = float(value)
                    P_x = float(temp['10'])
                    #value = degrees(pi/2-acos(float(value)))
                elif key == '220':#Y of OCS unitary vector
                    Az_2 = float(value)
                    P_y = -float(temp['20'])
                    #value = -degrees(pi/2-acos(float(value)))
                elif key == '230':#Z of OCS unitary vector
                    Az_3 = float(value)
                    P_z = float(temp['30'])
                    #arbitrary axis algorithm
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
                    temp['20'] = -(P_x*Ax_2+P_y*Ay_2+P_z*Az_2)
                    temp['30'] = P_x*Ax_3+P_y*Ay_3+P_z*Az_3
                    #world coordinates from OCS for auxiliary point
                    temp['11'] = (P_x+cos(radians(float(temp['50']))))*Ax_1+(P_y+sin(radians(float(temp['50']))))*Ay_1+P_z*Az_1
                    temp['21'] = -((P_x+cos(radians(float(temp['50']))))*Ax_2+(P_y+sin(radians(float(temp['50']))))*Ay_2+P_z*Az_2)
                    temp['31'] = (P_x+cos(radians(float(temp['50']))))*Ax_3+(P_y+sin(radians(float(temp['50']))))*Ay_3+P_z*Az_3

            if key == '0':

                if flag == 'face':#to do repeat we should calculate triangle width
                    #is material set in model?
                    no_color=True
                    if material_gallery:
                        for material in material_gallery:
                            if material.layer == temp['8']:
                                no_color=False
                    if no_color:#color is still not set for layer, so we use default
                        temp['8'] = 'default'
                    output[x] = self.make_triangle_1(x, temp)
                    if temp['12']!=temp['13'] or temp['22']!=temp['23'] or temp['32']!=temp['33']:
                        x += 1
                        output[x] = self.make_triangle_2(x, temp)
                    flag = False

                elif flag == 'block':
                    #material images are patterns? is material set in model?
                    no_color=True
                    if material_gallery:
                        for material in material_gallery:
                            if material.layer == temp['8']:
                                no_color=False
                                if material.pattern == True:
                                    temp['repeat']=True
                    if no_color:#color is still not set for layer, so we use default
                        temp['8'] = 'default'

                    if temp['2'] == '6planes':
                        output[x] = self.make_6planes(x, temp)

                    elif temp['2'] == 'box':
                        output[x] = self.make_box(x, temp)

                    elif temp['2'] == 'cylinder':
                        output[x] = self.make_cylinder(x, temp)

                    elif temp['2'] == 'cone':
                        output[x] = self.make_cone(x, temp)

                    elif temp['2'] == 'sphere':
                        output[x] = self.make_sphere(x, temp)

                    elif temp['2'] == 'circle':
                        output[x] = self.make_circle(x, temp)

                    elif temp['2'] == 'plane':
                        output[x] = self.make_plane(x, temp)

                    elif temp['2'] == 'floor':
                        output[x] = self.make_floor(x, temp)

                    elif temp['2'] == 'ceiling':
                        output[x] = self.make_ceiling(x, temp)

                    elif temp['2'] == 'light':
                        output[x] = self.make_light(x, temp)

                    flag = False

                if value == '3DFACE':
                    temp = {}#default values
                    flag = 'face'
                    x += 1
                elif value == 'INSERT':
                    temp = {'41': 1, '42': 1, '43': 1, '50': 0, '210': 0, '220': 0, '230': 1,'repeat': False}#default values
                    flag = 'block'
                    x += 1

        dxf_f.close()
        return output

    def is_repeat(self, repeat, rx, ry):
        if repeat:
            output = f'; repeat:{rx} {ry}'
            return output
        else:
            return ';'

    def make_6planes(self, x, temp):
        outstr = f'<a-entity id="box-{x}" \n'
        outstr += f'position="{temp["10"]} {temp["30"]} {temp["20"]}" \n'
        outstr += f'rotation="0 {temp["50"]} 0">\n'

        outstr += f'<a-plane id="box-{x}-bottom" \n'
        outstr += f'position="{float(temp["41"])/2} 0 {-float(temp["42"])/2}" \n'
        outstr += 'rotation="90 0 0" \n'
        outstr += f'width="{temp["41"]}" height="{temp["42"]}" \n'
        outstr += f'mixin="color-{temp["8"]}" \n'
        outstr += f'material="src: #image-{temp["8"]}'
        outstr += self.is_repeat(temp["repeat"], temp["41"], temp["42"])
        outstr += '">\n</a-plane> \n'

        outstr += f'<a-plane id="box-{x}-top" \n'
        outstr += f'position="{float(temp["41"])/2} {temp["43"]} {-float(temp["42"])/2}" \n'
        outstr += 'rotation="-90 0 0" \n'
        outstr += f'width="{temp["41"]}" height="{temp["42"]}" \n'
        outstr += f'mixin="color-{temp["8"]}" \n'
        outstr += f'material="src: #image-{temp["8"]}'
        outstr += self.is_repeat(temp["repeat"], temp["41"], temp["42"])
        outstr += '">\n</a-plane> \n'

        outstr += f'<a-plane id="box-{x}-front" \n'
        outstr += f'position="{float(temp["41"])/2} {float(temp["43"])/2} {-float(temp["42"])}" \n'
        outstr += 'rotation="0 180 0" \n'
        outstr += f'width="{temp["41"]}" height="{temp["43"]}" \n'
        outstr += f'mixin="color-{temp["8"]}" \n'
        outstr += f'material="src: #image-{temp["8"]}'
        outstr += self.is_repeat(temp["repeat"], temp["41"], temp["43"])
        outstr += '">\n</a-plane> \n'

        outstr += f'<a-plane id="box-{x}-back" \n'
        outstr += f'position="{float(temp["41"])/2} {float(temp["43"])/2} 0" \n'
        outstr += f'width="{temp["41"]}" height="{temp["43"]}" \n'
        outstr += f'mixin="color-{temp["8"]}" \n'
        outstr += f'material="src: #image-{temp["8"]}'
        outstr += self.is_repeat(temp["repeat"], temp["41"], temp["43"])
        outstr += '">\n</a-plane> \n'

        outstr += f'<a-plane id="box-{x}-right" \n'
        outstr += f'position="{float(temp["41"])} {float(temp["43"])/2} {-float(temp["42"])/2}" \n'
        outstr += 'rotation="0 90 0" \n'
        outstr += f'width="{temp["42"]}" height="{temp["43"]}" \n'
        outstr += f'mixin="color-{temp["8"]}" \n'
        outstr += f'material="src: #image-{temp["8"]}'
        outstr += self.is_repeat(temp["repeat"], temp["42"], temp["43"])
        outstr += '">\n</a-plane> \n'

        outstr += f'<a-plane id="box-{x}-left" \n'
        outstr += f'position="0 {float(temp["43"])/2} {-float(temp["42"])/2}" \n'
        outstr += 'rotation="0 -90 0" \n'
        outstr += f'width="{temp["42"]}" height="{temp["43"]}" \n'
        outstr += f'mixin="color-{temp["8"]}" \n'
        outstr += f'material="src: #image-{temp["8"]}'
        outstr += self.is_repeat(temp["repeat"], temp["42"], temp["43"])
        outstr += '">\n</a-plane> \n'

        outstr += '</a-entity>\n'
        outstr += f'<p>auxiliary="{temp["11"]} {temp["31"]} {temp["21"]}"</p>\n'
        return outstr

    def make_box(self, x, temp):
        outstr = f'<a-entity id="box-ent-{x}" \n'
        outstr += f'position="{temp["10"]} {temp["30"]} {temp["20"]}" \n'
        outstr += f'rotation="0 {temp["50"]} 0">\n'
        outstr += f'<a-box id="box-{x}" \n'
        outstr += f'position="{float(temp["41"])/2} {float(temp["43"])/2} {-float(temp["42"])/2}" \n'
        outstr += f'scale="{temp["41"]} {temp["43"]} {temp["42"]}" \n'
        outstr += f'mixin="color-{temp["8"]}" \n'
        outstr += f'material="src: #image-{temp["8"]}'
        outstr += self.is_repeat(temp["repeat"], temp["41"], temp["43"])
        outstr += '">\n</a-box>\n</a-entity>\n'
        return outstr

    def make_cone(self, x, temp):
        outstr = f'<a-entity id="cone-ent-{x}" \n'
        outstr += f'position="{temp["10"]} {temp["30"]} {temp["20"]}" \n'
        outstr += f'rotation="0 {temp["50"]} 0">\n'
        outstr += f'<a-cone id="cone-{x}" \n'
        outstr += f'position="0 {float(temp["43"])/2} 0" \n'
        outstr += f'scale="{temp["41"]} {temp["43"]} {temp["42"]}" \n'
        outstr += f'mixin="color-{temp["8"]}" \n'
        outstr += f'material="src: #image-{temp["8"]}'
        outstr += self.is_repeat(temp["repeat"], temp["41"], temp["43"])
        outstr += '">\n</a-cone>\n</a-entity>\n'
        return outstr

    def make_circle(self, x, temp):
        outstr = f'<a-circle id="circle-{x}" \n'
        outstr += f'position="{temp["10"]} {temp["30"]} {temp["20"]}" \n'
        outstr += f'rotation="-90 {temp["50"]} 0"\n'
        outstr += f'radius="{temp["41"]}" \n'
        outstr += f'mixin="color-{temp["8"]}" \n'
        outstr += f'material="src: #image-{temp["8"]}'
        outstr += self.is_repeat(temp["repeat"], temp["41"], temp["43"])
        outstr += '">\n</a-circle>\n'
        return outstr

    def make_cylinder(self, x, temp):
        outstr = f'<a-entity id="cylinder-ent-{x}" \n'
        outstr += f'position="{temp["10"]} {temp["30"]} {temp["20"]}" \n'
        outstr += f'rotation="0 {temp["50"]} 0">\n'
        outstr += f'<a-cylinder id="cylinder-{x}" \n'
        outstr += f'position="0 {float(temp["43"])/2} 0" \n'
        outstr += f'scale="{temp["41"]} {temp["43"]} {temp["42"]}" \n'
        outstr += f'mixin="color-{temp["8"]}" \n'
        outstr += f'material="src: #image-{temp["8"]}'
        outstr += self.is_repeat(temp["repeat"], temp["41"], temp["43"])
        outstr += '">\n</a-cylinder>\n</a-entity>\n'
        return outstr

    def make_sphere(self, x, temp):
        outstr = f'<a-entity id="sphere-ent-{x}" \n'
        outstr += f'position="{temp["10"]} {temp["30"]} {temp["20"]}" \n'
        outstr += f'rotation="0 {temp["50"]} 0">\n'
        outstr += f'<a-sphere id="sphere-{x}" \n'
        outstr += f'position="0 {temp["43"]} 0" \n'
        outstr += f'scale="{temp["41"]} {temp["43"]} {temp["42"]}" \n'
        outstr += f'mixin="color-{temp["8"]}" \n'
        outstr += f'material="src: #image-{temp["8"]}'
        outstr += self.is_repeat(temp["repeat"], temp["41"], temp["43"])
        outstr += '">\n</a-sphere>\n</a-entity>\n'
        return outstr

    def make_plane(self, x, temp):
        outstr = f'<a-entity id="plane-ent-{x}" \n'
        outstr += f'position="{temp["10"]} {temp["30"]} {temp["20"]}" \n'
        outstr += f'rotation="0 {temp["50"]} 0">\n'
        outstr += f'<a-plane id="plane-{x}" \n'
        outstr += f'position="{float(temp["41"])/2} {float(temp["43"])/2} 0" \n'
        outstr += f'width="{temp["41"]}" height="{temp["43"]}" \n'
        outstr += f'mixin="color-{temp["8"]}" \n'
        outstr += f'material="src: #image-{temp["8"]}'
        outstr += self.is_repeat(temp["repeat"], temp["41"], temp["43"])
        outstr += '">\n</a-plane>\n</a-entity>\n'
        return outstr

    def make_floor(self, x, temp):
        outstr = f'<a-entity id="floor-ent-{x}" \n'
        outstr += f'position="{temp["10"]} {temp["30"]} {temp["20"]}" \n'
        outstr += f'rotation="0 {temp["50"]} 0">\n'
        outstr += f'<a-plane id="floor-{x}" \n'
        outstr += f'position="{float(temp["41"])/2} 0 {-float(temp["42"])/2}" \n'
        outstr += f'rotation="-90 0 0"\n'
        outstr += f'width="{temp["41"]}" height="{temp["42"]}" \n'
        outstr += f'mixin="color-{temp["8"]}" \n'
        outstr += f'material="src: #image-{temp["8"]}'
        outstr += self.is_repeat(temp["repeat"], temp["41"], temp["42"])
        outstr += '">\n</a-plane>\n</a-entity>\n'
        return outstr

    def make_ceiling(self, x, temp):
        outstr = f'<a-entity id="ceiling-ent-{x}" \n'
        outstr += f'position="{temp["10"]} {temp["30"]} {temp["20"]}" \n'
        outstr += f'rotation="0 {temp["50"]} 0">\n'
        outstr += f'<a-plane id="ceiling-{x}" \n'
        outstr += f'position="{float(temp["41"])/2} 0 {-float(temp["42"])/2}" \n'
        outstr += f'rotation="90 0 0"\n'
        outstr += f'width="{temp["41"]}" height="{temp["42"]}" \n'
        outstr += f'mixin="color-{temp["8"]}" \n'
        outstr += f'material="src: #image-{temp["8"]}'
        outstr += self.is_repeat(temp["repeat"], temp["41"], temp["42"])
        outstr += '">\n</a-plane>\n</a-entity>\n'
        return outstr

    def make_triangle_1(self, x, temp):
        outstr = f'<a-triangle id="triangle-{x}" \n'
        outstr += f'geometry="vertexA:{temp["10"]} {temp["30"]} {temp["20"]}; \n'
        outstr += f'vertexB:{temp["11"]} {temp["31"]} {temp["21"]}; \n'
        outstr += f'vertexC:{temp["12"]} {temp["32"]} {temp["22"]}" \n'
        outstr += f'mixin="color-{temp["8"]}" \n'
        outstr += f'material="src: #image-{temp["8"]}; '
        if self.double_face:
            outstr += 'side: double; '
        outstr += '">\n</a-triangle> \n'
        return outstr

    def make_triangle_2(self, x, temp):
        outstr = f'<a-triangle id="triangle-{x}" \n'
        outstr += f'geometry="vertexA:{temp["10"]} {temp["30"]} {temp["20"]}; \n'
        outstr += f'vertexB:{temp["12"]} {temp["32"]} {temp["22"]}; \n'
        outstr += f'vertexC:{temp["13"]} {temp["33"]} {temp["23"]}" \n'
        outstr += f'mixin="color-{temp["8"]}" \n'
        outstr += f'material="src: #image-{temp["8"]}; '
        if self.double_face:
            outstr += 'side: double; '
        outstr += '">\n</a-triangle> \n'
        return outstr

    def make_light(self, x, temp):
        outstr = f'<a-entity id="light-{x}" \n'
        outstr += f'position="{temp["10"]} {temp["30"]} {temp["20"]}" \n'
        outstr += 'light="type: point; intensity: 0.75; distance: 50; decay: 2; '
        if self.shadows:
            outstr += 'castShadow: true;'
        outstr += '">\n</a-entity>\n'
        return outstr

    def extract_meshes(self):#abandoned, but interesting structure
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
            if flag == 'face':
                if key == '8':#layer name
                    temp[key] = value
                elif key == '10' or key == '11' or key == '12' or key == '13':#X position
                    temp[key] = value
                elif key == '20' or key == '21' or key == '22' or key == '23':#mirror Y position
                    value = -float(value)
                    temp[key] = value
                elif key == '30' or key == '31' or key == '32' or key == '33':#Z position
                    temp[key] = value
            elif flag == 'mesh':
                if key == '8':#layer name
                    temp[key] = value
                elif key == '10':#X position
                    temp_v[key] = value
                elif key == '20':#mirror Y position
                    value = -float(value)
                    temp_v[key] = value
                elif key == '30':#Z position
                    temp_v[key] = value
                    vertex[v] = temp_v
                    temp_v = {}
                    v += 1
                elif key == '71':#first vertex
                    #return vertex
                    temp_v = vertex[int(value)].copy()
                    temp['10'] = temp_v['10']
                    temp['20'] = temp_v['20']
                    temp['30'] = temp_v['30']
                elif key == '72':#second vertex
                    temp_v = vertex[int(value)].copy()
                    temp['11'] = temp_v['10']
                    temp['21'] = temp_v['20']
                    temp['31'] = temp_v['30']
                elif key == '73':#third vertex
                    temp_v = vertex[int(value)].copy()
                    temp['12'] = temp_v['10']
                    temp['22'] = temp_v['20']
                    temp['32'] = temp_v['30']
                    output[x] = temp
                    x += 1
                elif key == '74':#fourth vertex
                    temp2 = temp.copy()
                    temp_v = vertex[int(value)].copy()
                    temp2['10'] = temp_v['10']
                    temp2['20'] = temp_v['20']
                    temp2['30'] = temp_v['30']
                    temp2['11']=temp['10']; temp2['21']=temp['20']; temp2['31']=temp['30']
                    output[x] = temp2
                    temp = {}
                    temp2 = {}
                    x += 1
            if key == '0':
                if flag == 'face':
                    output[x] = temp
                    if temp['12']!=temp['13'] or temp['22']!=temp['23'] or temp['32']!=temp['33']:
                        temp2 = temp.copy()
                        temp2['11']=temp['12']; temp2['21']=temp['22']; temp2['31']=temp['32']
                        temp2['12']=temp['13']; temp2['22']=temp['23']; temp2['32']=temp['33']
                        x += 1
                        output[x] = temp2
                    flag = False
                if flag == 'mesh' and value != 'VERTEX':
                    flag = False
                if value == '3DFACE':
                    temp = {}#default values
                    flag = 'face'
                    x += 1
                elif value == 'VERTEX' and flag != 'mesh':
                    temp = {}
                    temp2 = {}
                    vertex = {}
                    temp_v = {}
                    flag = 'mesh'
                    x += 1
                    v = 1
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
    pattern = models.BooleanField(default=False)

    panels = [
        FieldPanel('layer'),
        ImageChooserPanel('image'),
        FieldPanel('pattern'),
        FieldPanel('color'),
]