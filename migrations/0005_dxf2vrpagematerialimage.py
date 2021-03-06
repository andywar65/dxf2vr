# -*- coding: utf-8 -*-
# Generated by Django 1.11.4 on 2017-09-20 16:02
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion
import modelcluster.fields


class Migration(migrations.Migration):

    dependencies = [
        ('wagtailimages', '0019_delete_filter'),
        ('dxf2vr', '0004_auto_20170920_1800'),
    ]

    operations = [
        migrations.CreateModel(
            name='Dxf2VrPageMaterialImage',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('sort_order', models.IntegerField(blank=True, editable=False, null=True)),
                ('layer', models.CharField(default='0', max_length=250)),
                ('color', models.CharField(default='white', max_length=250)),
                ('image', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to='wagtailimages.Image')),
                ('page', modelcluster.fields.ParentalKey(on_delete=django.db.models.deletion.CASCADE, related_name='material_images', to='dxf2vr.Dxf2VrPage')),
            ],
            options={
                'ordering': ['sort_order'],
                'abstract': False,
            },
        ),
    ]
