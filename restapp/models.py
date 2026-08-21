from django.db import models

# Create your models here.
class Category(models.Model):
    name = models.CharField(max_length=100)



class Menu(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField()
    date_Added = models.DateTimeField(auto_now_add=True)
    price = models.DecimalField(max_digits=6, decimal_places=2)
    Category = models.ForeignKey(Category, on_delete=models.CASCADE)
    last_updated = models.DateTimeField(auto_now=True)