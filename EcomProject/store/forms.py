from django import forms
from django.core.validators import MinLengthValidator

from .models import Product, Variant

class ProductForm(forms.ModelForm):
    product_image = forms.ImageField(required=True, error_messages={'invalid': ("Image File Only")},
                                       widget=forms.FileInput)
    class Meta:
        model = Product
        fields = ['product_name', 'slug', 'description', 'price', 'stock', 'category']

    def __init__(self, *args, **kwargs):
        super(ProductForm, self).__init__(*args, **kwargs)
        self.fields['product_name'].widget.attrs['placeholder'] = 'Enter Product Name'
        self.fields['slug'].widget.attrs['placeholder'] = 'Slug'
        self.fields['description'].widget.attrs['placeholder'] = 'Enter Description'
        self.fields['price'].widget.attrs['placeholder'] = 'Price'
        self.fields['stock'].widget.attrs['placeholder'] = 'Stock'
        self.fields['category'].widget.attrs['placeholder'] = 'Select Category'

        for field in self.fields:
            self.fields[field].widget.attrs['class'] = 'form-control'

    def clean(self):
        cleaned_data = super(ProductForm, self).clean()

    def clean_product_name(self):
        product_name = self.cleaned_data.get('product_name')
        if not product_name or product_name.isspace():
            raise forms.ValidationError("Product Name cannot be empty or contain only white spaces.")
        return product_name.strip()

    def clean_slug(self):
        slug = self.cleaned_data.get('slug')
        if not slug or slug.isspace():
            raise forms.ValidationError("Slug field cannot be empty or contain only white spaces.")
        return slug.strip()

    def clean_description(self):
        description = self.cleaned_data.get('description')
        if not description or description.isspace():
            raise forms.ValidationError("Description cannot be empty or contain only white spaces.")
        return description.strip()

class VariantForm(forms.ModelForm):
    class Meta:
        model = Variant
        fields = ['product', 'variant_category', 'variant_value']

    def __init__(self, *args, **kwargs):
        super(VariantForm, self).__init__(*args, **kwargs)
        self.fields['product'].widget.attrs['placeholder'] = 'Select Product Name'
        self.fields['variant_category'].widget.attrs['placeholder'] = 'Select Variant Category'
        self.fields['variant_value'].widget.attrs['placeholder'] = 'Enter Variant Value'
        for field in self.fields:
            self.fields[field].widget.attrs['class'] = 'form-control'


    def clean(self):
        cleaned_data = super(VariantForm, self).clean()

    def clean_variant_value(self):
        variant_value = self.cleaned_data.get('variant_value')
        if not variant_value or variant_value.isspace():
            raise forms.ValidationError("Description cannot be empty or contain only white spaces.")
        return variant_value.strip()
