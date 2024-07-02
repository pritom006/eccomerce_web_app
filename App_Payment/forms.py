from django import forms
from App_Payment.models import BillingAdress

class BillingForm(forms.ModelForm):
    class Meta:
        model = BillingAdress
        fields = ['address', 'zipcode', 'city', 'country']