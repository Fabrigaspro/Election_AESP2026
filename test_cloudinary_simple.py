import os
import django
import requests
from io import BytesIO

# Configure Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'election_project.settings')
django.setup()

def test_cloudinary_configuration():
    """
    Test concret de la configuration Cloudinary
    """
    print("🧪 TEST CONCRET CLOUDINARY")
    print("=" * 50)
    
    # 1. Test des variables d'environnement
    print("1. 📋 VARIABLES D'ENVIRONNEMENT")
    print("-" * 30)
    
    cloudinary_url = os.environ.get('CLOUDINARY_URL')
    cloud_name = os.environ.get('CLOUDINARY_CLOUD_NAME')
    api_key = os.environ.get('CLOUDINARY_API_KEY')
    api_secret = os.environ.get('CLOUDINARY_API_SECRET')
    
    print(f"CLOUDINARY_URL: {'✅' if cloudinary_url else '❌'}")
    if cloudinary_url:
        # Masque les informations sensibles
        masked_url = cloudinary_url.split('@')[0].split('//')[0] + '//***:***@' + cloudinary_url.split('@')[1]
        print(f"   Format: {masked_url}")
    
    print(f"CLOUDINARY_CLOUD_NAME: {'✅' if cloud_name else '❌'}")
    print(f"CLOUDINARY_API_KEY: {'✅' if api_key else '❌'}")
    print(f"CLOUDINARY_API_SECRET: {'✅' if api_secret else '❌'}")
    
    # 2. Test de la configuration Django
    print("\n2. ⚙️ CONFIGURATION DJANGO")
    print("-" * 30)
    
    from django.conf import settings
    print(f"ENVIRONMENT: {getattr(settings, 'ENVIRONMENT', 'Non défini')}")
    print(f"DEBUG: {settings.DEBUG}")
    print(f"DEFAULT_FILE_STORAGE: {getattr(settings, 'DEFAULT_FILE_STORAGE', 'Non défini')}")
    
    # 3. Test de la librairie Cloudinary
    print("\n3. 🔗 TEST LIBRAIRIE CLOUDINARY")
    print("-" * 30)
    
    try:
        import cloudinary
        import cloudinary.uploader
        
        # Vérifie la configuration automatique
        config = cloudinary.config()
        print(f"Cloud Name: {config.cloud_name}")
        print(f"API Key: {config.api_key[:8]}...")
        print(f"API Secret: {'***' + config.api_secret[-4:] if config.api_secret else 'Non'}")
        print(f"Secure: {getattr(config, 'secure', False)}")
        
        if not config.cloud_name:
            print("❌ Cloudinary n'est pas configuré")
            return False
            
        print("✅ Configuration Cloudinary détectée")
        
    except ImportError:
        print("❌ Librairie cloudinary non installée")
        return False
    except Exception as e:
        print(f"❌ Erreur configuration: {e}")
        return False
    
    # 4. TEST RÉEL : Upload d'une image
    print("\n4. 🚀 TEST RÉEL - UPLOAD D'IMAGE")
    print("-" * 30)
    
    try:
        # Télécharge une petite image de test depuis internet
        test_image_url = "https://res.cloudinary.com/demo/image/upload/w_100,h_100,c_fill/sample.jpg"
        response = requests.get(test_image_url)
        
        if response.status_code == 200:
            # Upload vers VOTRE Cloudinary
            result = cloudinary.uploader.upload(
                response.content,
                public_id="test_validation_railway",
                folder="tests"
            )
            
            print("✅ UPLOAD RÉUSSI !")
            print(f"   URL: {result['secure_url']}")
            print(f"   Public ID: {result['public_id']}")
            print(f"   Format: {result['format']}")
            print(f"   Taille: {result['bytes']} bytes")
            
            # Test de l'URL générée
            test_response = requests.head(result['secure_url'])
            print(f"   Accessible: {'✅' if test_response.status_code == 200 else '❌'}")
            
            # Nettoyage : supprime l'image de test
            #cloudinary.uploader.destroy(result['public_id'])
            #print("   🧹 Image test supprimée")
            
            return True
            
        else:
            print("❌ Impossible de télécharger l'image de test")
            return False
            
    except Exception as e:
        print(f"❌ Erreur pendant l'upload: {e}")
        return False
    
    print("\n" + "=" * 50)
    print("🎉 TEST TERMINÉ")

if __name__ == "__main__":
    success = test_cloudinary_configuration()
    
    if success:
        print("\n✅ ✅ ✅ TOUT FONCTIONNE PARFAITEMENT !")
        print("Votre configuration Cloudinary est correcte.")
    else:
        print("\n❌ ❌ ❌ PROBLEMES DETECTES !")
        print("Vérifiez votre configuration Cloudinary.")