from django import forms

class SearchForm(forms.Form):
    phone_number = forms.CharField(max_length=20, label="Phone Number")
    description = forms.CharField(widget=forms.Textarea, required=False, label="Details")
    email = forms.EmailField(label="Email for Report (if new)")
