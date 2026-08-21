from django.shortcuts import render

from restapp import models

# Create your views here.

class Category(models.Model):
    name = models.CharField(max_length=100)



class Menu(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField()
    date_Added = models.DateTimeField(auto_now_add=True)
    price = models.DecimalField(max_digits=6, decimal_places=2)
    last_updated = models.DateTimeField(auto_now=True)
