# forms.py
from django import forms
from .models import Candidate

class CandidateForm(forms.ModelForm):
    class Meta:
        model = Candidate
        fields = [
            'nom', 'prenom', 'cycle', 'specialite', 'niveau',
            'slogan', 'photo_url', 'programme_pdf',
            'bureau_name', 'bureau_color'
        ]
        widgets = {
            'bureau_color': forms.TextInput(attrs={'type': 'color'}),
            'programme_pdf': forms.FileInput(attrs={
                'accept': '.pdf',
                'class': 'form-control'
            }),
            'photo_url': forms.FileInput(attrs={
                'accept': 'image/*',
                'class': 'form-control'
            })
        }
    
    def clean_programme_pdf(self):
        fichier = self.cleaned_data.get('programme_pdf')
        if fichier:
            # Vérifier l'extension
            if not fichier.name.lower().endswith('.pdf'):
                raise forms.ValidationError("Seuls les fichiers PDF sont autorisés.")
            
            # Vérifier la taille (10MB max)
            if fichier.size > 5 * 1024 * 1024:
                raise forms.ValidationError("Le fichier PDF ne doit pas dépasser 5MB.")
        
        return fichier
    
    def clean_photo_url(self):
        image = self.cleaned_data.get('photo_url')
        if image:
            # Vérifier la taille (5MB max pour les images)
            if image.size > 3 * 1024 * 1024:
                raise forms.ValidationError("L'image ne doit pas dépasser 3MB.")
        
        return image