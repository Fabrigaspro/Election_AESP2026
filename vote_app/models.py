# vote_app/models.py

from django.db import models
from django.contrib.auth.models import User
from cloudinary_storage.storage import RawMediaCloudinaryStorage,  MediaCloudinaryStorage
from cloudinary.models import CloudinaryField
from cloudinary.uploader import destroy
from django.utils import timezone
from datetime import timedelta
import secrets
# Modèle pour étendre le modèle User de base de Django avec nos champs personnalisés
class Profile(models.Model):

    ROLE_CHOICES = [
        ('admin', 'Administrateur'),
        ('student', 'Étudiant'),
    ]
    # Statuts possibles pour un utilisateur
    STATUS_CHOICES = [
        ('pending', 'En attente'),
        ('validated', 'Validé'),
        ('rejected', 'Rejeté'),
    ]
    
    # Cycles disponibles
    CYCLE_CHOICES = [
        ('bts', 'BTS'),
        ('hnd', 'HND'),
        ('lipro', 'Licence Professionnelle'),
        ('litech', 'Licence de Technologie'),
        ('bachelor', 'Bachelor of Technology'),
        ('master', 'Master'),
        ('ingenieur', 'Ingénieur'),
    ]

    # Spécialités par cycle
    SPECIALITE_BTS = [
        ('BAT', 'Bâtiment'),
        ('CHAU', 'Chaudronnerie'),
        ('CM', 'Construction Métallique'),
        ('ECOM', 'E-Commerce et Marketing Numérique'),
        ('ET', 'Électrotechnique'),
        ('GL', 'Génie Logiciel'),
        ('GTO', 'Géomètre Topographe'),
        ('IWD', 'Infographie et Web Design'),
        ('IIA', 'Informatique Industrielle et Automatisme'),
        ('IP', 'Ingénierie Pétrolière'),
        ('MECATRO', 'Mécatronique'),
        ('MGA', 'Mines et Géologie Appliquée'),
        ('RES', 'Réseau et Sécurité'),
        ('TELECOM', 'Télécommunications'),
        ('TP', 'Travaux Publics'),
        ('URBA', 'Urbanisme'),
        
    ]

    SPECIALITE_LICENCEPRO = [
        ('ASR', 'Administration et Securites Reseaux'),
        ('BAT', 'Bâtiment'),
        ('GEII', 'Génie Electrique et Informatique Industrielle'),
        ('GL', 'Génie Logiciel'),
        ('QHSE', 'Qualite-Hygiene-Securite-Environnement'),
        ('SIR', 'Systeme Informatique et Réseaux'),
        ('TELECOM', 'Telecommunication et Reseaux'),
        ('TP', 'Travaux Publics'),
        ('URBA', 'Urbanisme'),
    ]
    SPECIALITE_LICENCETECH = [
        ('GEII', 'Génie Electrique et Informatique Industrielle'),
        ('GCE', 'Génie Civil'),
        ('GL', 'Génie Logiciel')
    ]

    SPECIALITE_MASTER = SPECIALITE_LICENCEPRO

    SPECIALITE_HND = [
        ('BST', 'Building Science and Technology'),
        ('CET', 'Civil Engineering and Technology'),
        ('CE', 'Computer Engineering'),
        ('CGWD', 'Computer Graphic and web Design'),
        ('DBM', 'Database Management'),
        ('EPS', 'Electrical Power Systems'),
        ('ECT', 'Electrotechnics'),
        ('NWSE', 'Networks and Security'),
        ('SWE', 'Software Engineering'),
        ('TELECOM', 'Telecommunications'),
        ('TOPO', 'Topography'),
    ]

    SPECIALITE_BACHELOR  = [
        ('CNSM', 'Computer Network and System Maintenance'),
        ('SWE', 'Software Engineering'),
        ('EEE', 'Electrical and Electronic Engineering'),
        ('CE', 'Civil Engineering'),
    ]

    SPECIALITE_INGENIEUR = [
        ('Prépa', 'Classe Preparatoire'),
        ('GCE', 'Génie Civil'),
        ('GESI', 'Génie Électrique et Systèmes Intélligents'),
        ('GM', 'Génie Mécanique'),
        ('GMA', 'Génie Mécatronique et Antomobile'),
        ('GIT', 'Génie Informatique et Télécommunication'),
        ('QHSE', 'Qualité Higiène Sécurité Environnement'),
    ]
    TIMEOUT = 3 # Temps d'Expiration de chaque session en min

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    matricule = models.CharField(max_length=100, default='MAT')
    campus = models.CharField(max_length=100 , default='Bonamoussadi')
    cycle = models.CharField(max_length=100, choices=CYCLE_CHOICES, default='bts')
    specialite = models.CharField(max_length=100, blank=True, null=True)
    niveau = models.IntegerField(blank=True)
    telephone = models.CharField(max_length=15, blank=True)
    photo = CloudinaryField('image', folder='photos/')
    recu = CloudinaryField('image', folder='recus/')
    
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='student')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    has_voted = models.BooleanField(default=False)
    is_admin = models.BooleanField(default=False)
    is_connected = models.BooleanField(default=False)
    last_activity = models.DateTimeField(default=timezone.now)
    session_token = models.CharField(max_length=64, blank=True, null=True, unique=True)
    session_expires = models.DateTimeField(null=True, blank=True)  # Expiration de session
    
    def generate_session_token(self):
        """Génère un nouveau token de session avec expiration"""
        self.session_token = secrets.token_urlsafe(32)
        self.session_expires = timezone.now() + timedelta(minutes=self.TIMEOUT)  # Expire dans le temp defini TIMEOUT
        if self.is_admin == 'admin':
            self.session_expires = timezone.now() + timedelta(hours= 24)  # Reset à 10 min
        self.is_connected = True
        self.save()
        return self.session_token
    
    def update_activity(self, request=None):
        """Met à jour l'activité et prolonge la session"""
        self.last_activity = timezone.now()
        self.session_expires = timezone.now() + timedelta(minutes=self.TIMEOUT)  # Reset à 3 min
        if self.is_admin == 'admin':
            self.session_expires = timezone.now() + timedelta(hours= 24)  # Reset à 24h

        self.save(update_fields=['last_activity', 'session_expires'])

    def invalidate_session(self):
        """Invalide la session (déconnexion normale)"""
        self.is_connected = False
        self.session_token = None
        self.session_expires = None
        self.save()

    @property
    def has_active_session(self):
        """Vérifie si une session est active (non expirée)"""
        print("self.is_admin : ", self.is_admin)
        if not self.is_admin and (not self.is_connected or not self.session_token or not self.session_expires):
            # Session expirée - auto-nettoyage
            self.is_connected = False
            self.save()
            return False
        print("self.is_admin : ", self.is_admin)
        
        if self.is_admin and self.is_connected :
            return True
        
        print("self.is_admin : ", self.is_admin)
        # Vérifier si la session est expirée
        if timezone.now() > self.session_expires:
            # Session expirée - auto-nettoyage
            self.is_connected = False
            self.session_token = None
            self.session_expires = None
            self.save()
            return False
        
        return True
    
    @property
    def is_actually_connected(self):
        """Vérifie la connexion basée sur l'activité récente"""
        if not self.last_activity:
            return False
        
        timeout_duration = timedelta(minutes=self.TIMEOUT)
        timeout_threshold = timezone.now() - timeout_duration
        
        return self.last_activity > timeout_threshold
    
    def validate_session(self, request):
        """Valide que la session actuelle est la bonne"""
        current_token = request.session.get('session_token')
        return current_token == self.session_token
    
    def force_disconnect(self):
        """Force la déconnexion de l'utilisateur"""
        self.last_activity = timezone.now() - timedelta(days=1)  # Date dans le passé
        self.is_connected = False
        self.save(update_fields=['last_activity', 'is_connected'])
        
    def save(self, *args, **kwargs):
        """Sauvegarde le profil avec gestion sécurisée des images Cloudinary"""
        
        # Initialiser les variables pour suivre les changements
        old_photo_public_id = None
        old_recu_public_id = None
        
        # Si c'est une mise à jour (objet existant)
        if self.pk:
            try:
                old_instance = Profile.objects.get(pk=self.pk)
                print("=== DEBUG DÉBUT ===")
                # 1. Gestion changement Photo
                if old_instance.photo:
                    print("Ancienne photo existe")
                    # Vérifier si un nouveau fichier a été uploadé
                    if hasattr(self.photo, 'file'):  # C'est un nouveau fichier uploadé
                        print("Nouveau fichier photo uploadé")
                        old_photo_public_id = getattr(old_instance.photo, 'public_id', None)
                    else:
                        # Comparer les public_id si les deux sont des objets Cloudinary
                        old_public_id = getattr(old_instance.photo, 'public_id', None)
                        new_public_id = getattr(self.photo, 'public_id', None)
                        
                        print(f"Comparaison: {old_public_id} vs {new_public_id}")
                        
                        if old_public_id and new_public_id and old_public_id != new_public_id:
                            print("Photo a changé")
                            old_photo_public_id = old_public_id
                
                # 2. Gestion changement Recu AESP
                if old_instance.recu:
                    print("Ancienne recu existe")
                    # Vérifier si un nouveau fichier a été uploadé
                    if hasattr(self.recu, 'file'):  # C'est un nouveau fichier uploadé
                        print("Nouveau fichier recu uploadé")
                        old_recu_public_id = getattr(old_instance.recu, 'public_id', None)
                    else:
                        # Comparer les public_id si les deux sont des objets Cloudinary
                        old_public_id = getattr(old_instance.recu, 'public_id', None)
                        new_public_id = getattr(self.recu, 'public_id', None)
                        
                        print(f"Comparaison: {old_public_id} vs {new_public_id}")
                        
                        if old_public_id and new_public_id and old_public_id != new_public_id:
                            print("Recu a changé")
                            old_recu_public_id = old_public_id
                
                print(f"À supprimer - Photo: {old_photo_public_id}, Recu: {old_recu_public_id}")
                print("=== DEBUG FIN ===")
            
            except Profile.DoesNotExist:
                pass
        self.matricule = self.user.username
        # Sauvegarder d'abord l'objet
        super().save(*args, **kwargs)  
        # Supprimer les anciennes images APRÈS la sauvegarde
        try:
            if old_photo_public_id:
                destroy(old_photo_public_id)
                print(f"✅ Ancienne photo supprimée: {old_photo_public_id}")
                
            if old_recu_public_id:
                destroy(old_recu_public_id)
                print(f"✅ Ancien reçu supprimé: {old_recu_public_id}")
                
        except Exception as e:
            print(f"⚠️ Erreur lors de la suppression des anciennes images: {e}")
    
    def delete(self, *args, **kwargs):
        """Supprime l'image Cloudinary lors de la suppression de l'objet"""
        try:
            # Vérifier si l'image existe et a un public_id
            if self.photo and hasattr(self.photo, 'public_id'):
                public_id = self.photo.public_id
                if public_id:
                    destroy(public_id)
                    print(f"✅ Image Cloudinary supprimée: {public_id}")
            if self.recu and hasattr(self.recu, 'public_id'):
                public_id = self.recu.public_id
                if public_id:
                    destroy(public_id)
                    print(f"✅ Image Cloudinary supprimée: {public_id}")
        except Exception as e:
            print(f"⚠️ Erreur lors de la suppression de l'image Cloudinary: {e}")
        
        # Toujours appeler super().delete() même en cas d'erreur
        super().delete(*args, **kwargs)

    def get_fullname(self):
        return f'{self.user.first_name} {self.user.last_name}'
    
    def get_cycle_display(self):
        for code, name in self.CYCLE_CHOICES:
            if code == self.cycle:
                return name
        return self.cycle
    
    # Propriété pour afficher le libellé de la spécialité
    @property
    def specialite_display(self):
        specialites_dict = dict(
            self.SPECIALITE_BTS + 
            self.SPECIALITE_HND +
            self.SPECIALITE_LICENCEPRO + 
            self.SPECIALITE_LICENCETECH + 
            self.SPECIALITE_BACHELOR +
            self.SPECIALITE_MASTER + 
            self.SPECIALITE_INGENIEUR
        )
        print(specialites_dict)
        print(specialites_dict.get(self.specialite, self.specialite))
        return specialites_dict.get(self.specialite, self.specialite)

    def __str__(self):
        return f"Profil de {self.user.username}"

    class Meta:
        verbose_name = "Profil"
        verbose_name_plural = "Profils"
    
    def __str__(self):
        return f"Profil de {self.user.username}"

class Candidate(models.Model):

    # Cycles disponibles
    CYCLE_CHOICES = Profile.CYCLE_CHOICES

    # Spécialités
    SPECIALITE_BTS = Profile.SPECIALITE_BTS
    SPECIALITE_HND = Profile.SPECIALITE_HND

    SPECIALITE_LICENCEPRO = Profile.SPECIALITE_LICENCEPRO
    SPECIALITE_LICENCETECH = Profile.SPECIALITE_LICENCETECH
    SPECIALITE_BACHELOR = Profile.SPECIALITE_BACHELOR

    SPECIALITE_MASTER = Profile.SPECIALITE_MASTER

    SPECIALITE_INGENIEUR = Profile.SPECIALITE_INGENIEUR

    # Informations personnelles
    nom = models.CharField(max_length=100)
    prenom = models.CharField(max_length=100)
    name = models.CharField(max_length=200, unique=True, blank=True)  # blank=True car généré auto
    
    # Informations académiques
    cycle = models.CharField(max_length=100, choices=CYCLE_CHOICES, default='bts')
    specialite = models.CharField(max_length=100)
    niveau = models.CharField(max_length=50)
    campus = models.CharField(max_length=100 , default='Bonamoussadi')
    
    # Campagne
    slogan = models.TextField()
    
    # Image du candidat
    photo_url = CloudinaryField('image', folder='candidats/')
    
    # CORRECTION MAJEURE ICI : Utilisation de CloudinaryField avec resource_type='auto'
    programme_pdf = CloudinaryField(
        'Programme électoral (PDF)',
        resource_type='auto', # Important pour éviter la corruption des PDF
        folder='programmes_pdf/',
        null=True,
        blank=True
    )

    # Statistiques
    votes = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    # Champs Bureau
    bureau_name = models.CharField(max_length=100, default='Bureau', verbose_name='Nom du Bureau' )
    bureau_color = models.CharField(max_length=7, default='#3498db', verbose_name='Couleur du Bureau')

    def save(self, *args, **kwargs):
        # Générer automatiquement le name complet
        if not self.name and self.prenom and self.nom:
            self.name = f"{self.prenom} {self.nom}"
        
        # Initialiser les variables pour suivre les changements
        old_photo_public_id = None
        old_pdf_public_id = None
        old_instance = None
    
        # Si c'est une mise à jour (objet existant)
        if self.pk:
            try:
                old_instance = Candidate.objects.get(pk=self.pk)   
                print("=== DEBUG DÉBUT ===")
                # 1. Gestion changement Photo
                if old_instance.photo_url:
                    print("Ancienne photo existe")
                    # Vérifier si un nouveau fichier a été uploadé
                    if hasattr(self.photo_url, 'file'):  # C'est un nouveau fichier uploadé
                        print("Nouveau fichier photo uploadé")
                        old_photo_public_id = getattr(old_instance.photo_url, 'public_id', None)
                    else:
                        # Comparer les public_id si les deux sont des objets Cloudinary
                        old_public_id = getattr(old_instance.photo_url, 'public_id', None)
                        new_public_id = getattr(self.photo_url, 'public_id', None)
                        
                        print(f"Comparaison: {old_public_id} vs {new_public_id}")
                        
                        if old_public_id and new_public_id and old_public_id != new_public_id:
                            print("Photo a changé")
                            old_photo_public_id = old_public_id
    
                # 2. Gestion changement PDF 
                if old_instance.programme_pdf:
                    print("Ancien PDF existe")
                    
                    # Vérifier si un nouveau fichier a été uploadé
                    if hasattr(self.programme_pdf, 'file'):  # C'est un nouveau fichier uploadé
                        print("Nouveau fichier PDF uploadé")
                        old_pdf_public_id = getattr(old_instance.programme_pdf, 'public_id', None)
                    else:
                        # Comparer les public_id si les deux sont des objets Cloudinary
                        old_public_id = getattr(old_instance.programme_pdf, 'public_id', None)
                        new_public_id = getattr(self.programme_pdf, 'public_id', None)
                        
                        print(f"Comparaison PDF: {old_public_id} vs {new_public_id}")
                        
                        if old_public_id and new_public_id and old_public_id != new_public_id:
                            print("PDF a changé")
                            old_pdf_public_id = old_public_id
                
                print(f"À supprimer - Photo: {old_photo_public_id}, PDF: {old_pdf_public_id}")
                print("=== DEBUG FIN ===")
                
                # Récupération des votes
                try:
                    from vote_app.models import Vote
                    self.votes = Vote.objects.filter(candidate=old_instance).count()
                except:
                    pass
                    
            except Candidate.DoesNotExist:
                pass
    
        # Sauvegarder d'abord l'objet (CloudinaryField sera converti automatiquement)
        super().save(*args, **kwargs)  
        
        # Supprimer les anciens fichiers APRÈS la sauvegarde réussie
        try:
            if old_photo_public_id:
                destroy(old_photo_public_id)
                print(f"✅ Ancienne photo supprimée: {old_photo_public_id}")
            
            if old_pdf_public_id:
                destroy(old_pdf_public_id, resource_type='auto') 
                print(f"✅ Ancien programme supprimé: {old_pdf_public_id}")
        except Exception as e:
            print(f"⚠️ Erreur lors du nettoyage Cloudinary: {e}")

    def delete(self, *args, **kwargs):
        """Supprime les fichiers Cloudinary lors de la suppression de l'objet"""
        try:
            # Suppression Photo
            if self.photo_url and hasattr(self.photo_url, 'public_id'):
                public_id = self.photo_url.public_id
                if public_id:
                    destroy(public_id)
                    print(f"✅ Image Cloudinary supprimée: {public_id}")
            
            # Suppression PDF
            if self.programme_pdf and hasattr(self.programme_pdf, 'public_id'):
                public_id = self.programme_pdf.public_id
                if public_id:
                    destroy(public_id, resource_type='auto')
                    print(f"✅ PDF Cloudinary supprimé: {public_id}")

        except Exception as e:
            print(f"⚠️ Erreur lors de la suppression Cloudinary: {e}")
        
        super().delete(*args, **kwargs)

    def __str__(self):
        return self.name if self.name else "Candidat sans nom"
    
    
    @property
    def photo_link(self):
        if self.photo_url:
            return self.photo_url.url
        return None
 
    @property
    def programme_url(self):
        if self.programme_pdf :
            return self.programme_pdf.url
        return None
    
    def get_cycle_display(self):
        return dict(self.CYCLE_CHOICES).get(self.cycle, self.cycle)

    @property
    def specialite_display(self):
        specialites_dict = dict(
            self.SPECIALITE_BTS + 
            self.SPECIALITE_HND +
            self.SPECIALITE_LICENCEPRO + 
            self.SPECIALITE_LICENCETECH + 
            self.SPECIALITE_BACHELOR +
            self.SPECIALITE_MASTER + 
            self.SPECIALITE_INGENIEUR
        )
        print(specialites_dict)
        print(specialites_dict.get(self.specialite, self.specialite))
        return specialites_dict.get(self.specialite, self.specialite)

    @property
    def full_name(self):
        return f"{self.prenom} {self.nom}"
# Modèle simple pour gérer l'état global de l'élection
class ElectionState(models.Model):
    STATUS_CHOICES = [
        ('pending', 'En attente'),
        ('active', 'Active'),
        ('closed', 'Terminée'),
    ]
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')

    # Assurer qu'il n'y a qu'une seule instance de ce modèle
    def save(self, *args, **kwargs):
        self.pk = 1
        if self.status == 'pending':
            candidates = Candidate.objects.all()
            for candidate in candidates:
                candidate.votes = 0
                candidate.save()
            
            Vote.objects.all().delete() # eface tous les votes
            # Réinitialiser le statut "a voté" pour tous les utilisateurs
            Profile.objects.all().update(has_voted=False)

        super(ElectionState, self).save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        pass # Empêcher la suppression

    @classmethod
    def load(cls):
        obj, created = cls.objects.get_or_create(pk=1)
        return obj

    def __str__(self):
        return f"État de l'élection : {self.get_status_display()}"

class Vote(models.Model):
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='votes')
    candidate = models.ForeignKey(Candidate, on_delete=models.CASCADE, related_name='vote_records')
    voted_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['profile',]
        ordering = ['-voted_at']
    
    def save(self, *args, **kwargs):
        self.candidate.save()
        super().save(*args, **kwargs)  

    def delete(self, *args, **kwargs):
        print("self.profile.has_voted : ", self.profile.has_voted)
        self.profile.has_voted = False
        self.profile.save()
        print("self.profile.has_voted : ", self.profile.has_voted)

        super().delete(*args, **kwargs)
        self.candidate.save()

    
    def __str__(self):
        return f"{self.profile.matricule} a voté pour {self.candidate.name}"