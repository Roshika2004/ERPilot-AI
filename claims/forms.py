from django import forms
from .models import Claim

class ClaimForm(forms.ModelForm):

    class Meta:

        model = Claim

        fields = [
            'title',
            'amount',
            'invoice'
        ]

        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter claim title (e.g., Hotel, Flight, Meal)',
                'required': 'required'
            }),
            'amount': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter amount in rupees',
                'step': '0.01',
                'min': '0',
                'required': 'required'
            }),
            'invoice': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': '.pdf,.jpg,.jpeg,.png',
                'required': 'required'
            })
        }

        labels = {
            'title': 'Claim Title',
            'amount': 'Amount (₹)',
            'invoice': 'Upload Invoice (PDF/JPG/PNG)'
        }