import os
import django
import sys

# Configure Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'election_project.settings')
django.setup()

from django.core.files import File
from vote_app.models import Candidate  # Adaptez avec vos modèles

def force_cloudinary_migration():
    """
    Force la migration de toutes les images vers Cloudinary
    """
    print("🚀 MIGRATION FORCÉE VERS CLOUDINARY")
    print("=" * 50)
    
    # Liste tous vos modèles avec des images
    models_to_migrate = [Candidate]  # Ajoutez d'autres modèles si nécessaire
    
    for model in models_to_migrate:
        print(f"\n🔍 Traitement du modèle: {model.__name__}")
        
        objects_with_images = model.objects.exclude(photo_url__isnull=True).exclude(photo_url='')
        total = objects_with_images.count()
        
        print(f"📊 {total} objet(s) avec image(s) à migrer")
        
        success_count = 0
        error_count = 0
        
        for obj in objects_with_images:
            try:
                print(f"\n🔄 Traitement: {obj}")
                print(f"   📁 Image actuelle: {obj.photo_url.name}")
                print(f"   🔗 URL actuelle: {obj.photo_url.url}")
                
                # Vérifie si l'image est déjà sur Cloudinary
                if 'cloudinary' in obj.photo_url.url:
                    print("   ✅ Déjà sur Cloudinary - Ignoré")
                    success_count += 1
                    continue
                
                # Vérifie si le fichier existe localement
                if hasattr(obj.photo_url, 'path') and os.path.exists(obj.photo_url.path):
                    print("   📍 Fichier local trouvé - Migration...")
                    
                    # Ouvre et ré-enregistre (déclenche upload Cloudinary)
                    with open(obj.photo_url.path, 'rb') as f:
                        django_file = File(f)
                        obj.photo_url.save(obj.photo_url.name, django_file, save=True)
                    
                    print(f"   ✅ Migré vers Cloudinary")
                    print(f"   🔗 Nouvelle URL: {obj.photo_url.url}")
                    success_count += 1
                    
                else:
                    print("   ❌ Fichier local non trouvé")
                    error_count += 1
                    
            except Exception as e:
                print(f"   ❌ Erreur: {str(e)}")
                error_count += 1
        
        # Résumé par modèle
        print(f"\n📈 {model.__name__}: {success_count} réussis, {error_count} erreurs")
    
    print("\n🎉 MIGRATION TERMINÉE!")

if __name__ == "__main__":
    force_cloudinary_migration()