from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from allauth.account.signals import user_signed_up
import requests
from django.core.files.base import ContentFile

# Create your models here.
class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    avatar = models.ImageField(upload_to='profile_images/', null=True, blank=True)
    
    def __str__(self):
        return f"{self.user.username}'s Profile"

# Create a Profile instance automatically when a new user is created
@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    instance.profile.save()
    
# Import profile picture from social account
@receiver(user_signed_up)
def populate_profile(sender, user, **kwargs):
    """Fetch and save profile picture from social account upon signup."""
    if 'sociallogin' in kwargs:
        social_login = kwargs['sociallogin']
        
        if social_login.account.provider == 'google':
            picture_url = social_login.account.extra_data.get('picture')
            
            if picture_url:
                try:
                    response = requests.get(picture_url)
                    if response.status_code == 200:
                        user.profile.avatar.save(
                            f"{user.username}_google_avatar.jpg",
                            ContentFile(response.content),
                            save=True
                        )
                except Exception:
                    # Silently fail if unable to download image
                    pass

# Favorite Pokémon model
class FavoritePokemon(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='favorites')
    pokemon_id = models.IntegerField()
    pokemon_name = models.CharField(max_length=100)
    added_on = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('user', 'pokemon_id')
        
    def __str__(self):
        return f"{self.user.username} - {self.pokemon_name}"
