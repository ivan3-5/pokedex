from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from . import pokeapi

# Create your views here.
def home(request):
    """Render the homepage with random featured Pokémon."""
    featured_pokemon = pokeapi.get_random_pokemon(4)
    
    # Get favorite status for each pokemon if user is authenticated
    favorite_ids = set()
    if request.user.is_authenticated:
        from .models import FavoritePokemon
        favorite_ids = set(FavoritePokemon.objects.filter(
            user=request.user
        ).values_list('pokemon_id', flat=True))
    
    # Add favorite flag to each pokemon
    for pokemon in featured_pokemon:
        pokemon['is_favorite'] = pokemon['id'] in favorite_ids
    
    return render(request, 'home.html', {
        'featured_pokemon': featured_pokemon
    })
    
def search_pokemon(request):
    """Search for a Pokémon by name with pagination."""
    query = request.GET.get('q', '')
    page = int(request.GET.get('page', 1))
    results_per_page = 24
    results = []
    
    if query:
        all_results = pokeapi.search(query)
        
        # Pagination logic
        total_results = len(all_results)
        total_pages = (total_results + results_per_page - 1) // results_per_page
        
        # Ensure page is within valid range
        if page < 1:
            page = 1
        elif page > total_pages and total_pages > 0:
            page = total_pages
        
        # Calculate slice indices for current page
        start_idx = (page - 1) * results_per_page
        end_idx = start_idx + results_per_page
        
        # Get the portion of results for current page
        results = all_results[start_idx:end_idx]
        
        # Get full pokemon data for each result
        detailed_results = []
        for pokemon in results:
            pokemon_data = pokeapi.get_pokemon(pokemon['id'])
            if pokemon_data:
                detailed_results.append(pokemon_data)
        
        # Get favorite status for each pokemon if user is authenticated
        favorite_ids = set()
        if request.user.is_authenticated:
            from .models import FavoritePokemon
            favorite_ids = set(FavoritePokemon.objects.filter(
                user=request.user
            ).values_list('pokemon_id', flat=True))
        
        # Add favorite flag to each pokemon
        for pokemon in detailed_results:
            pokemon['is_favorite'] = pokemon['id'] in favorite_ids
        
        return render(request, 'pokemon/search.html', {
            'query': query,
            'results': detailed_results,
            'page': page,
            'total_pages': total_pages,
            'total_results': total_results
        })
    
    return render(request, 'pokemon/search.html', {
        'query': query,
        'results': results
    })
    
def pokemon_details(request, name_or_id):
    """Display details for a specific Pokémon."""
    pokemon_data = pokeapi.get_pokemon(name_or_id)
    
    if not pokemon_data:
        return render(request, 'pokemon/not_found.html', {'name_or_id': name_or_id})
    
    is_favorite = False
    if request.user.is_authenticated:
        from .models import FavoritePokemon
        is_favorite = FavoritePokemon.objects.filter(
            user=request.user, 
            pokemon_id=pokemon_data['id']
        ).exists()
        
    return render(request, 'pokemon/details.html', {
        'pokemon': pokemon_data,
        'is_favorite': is_favorite
    })
    
@login_required
def profile(request):
    """Display user profile."""
    from .models import FavoritePokemon
    favorite_count = FavoritePokemon.objects.filter(user=request.user).count()
    return render(request, 'account/profile.html', {
        'favorite_count': favorite_count
    })
    
@login_required
def favorites(request):
    """Display user's favorite Pokémon with pagination and search."""
    from .models import FavoritePokemon
    
    # Get search query and pagination parameters
    query = request.GET.get('q', '').lower()
    page = int(request.GET.get('page', 1))
    results_per_page = 24
    
    # Get favorites with optional search filter
    user_favorites = FavoritePokemon.objects.filter(user=request.user).order_by('-added_on')
    
    # Get all favorite IDs for easy lookup
    favorite_ids = set(user_favorites.values_list('pokemon_id', flat=True))
    
    # Get all favorite pokemon data
    all_favorite_pokemon = []
    for fav in user_favorites:
        pokemon_data = pokeapi.get_pokemon(fav.pokemon_id)
        if pokemon_data:
            # Mark as favorite since we're on the favorites page
            pokemon_data['is_favorite'] = True
            all_favorite_pokemon.append(pokemon_data)
    
    # Apply search filter if query exists
    if query:
        filtered_favorites = [
            pokemon for pokemon in all_favorite_pokemon
            if query in pokemon['name'].lower() or 
               str(pokemon['id']) == query or
               any(query in type_info['type']['name'].lower() for type_info in pokemon.get('types', []))
        ]
    else:
        filtered_favorites = all_favorite_pokemon
    
    # Pagination logic
    total_results = len(filtered_favorites)
    total_pages = (total_results + results_per_page - 1) // results_per_page if total_results > 0 else 1
    
    # Ensure page is within valid range
    if page < 1:
        page = 1
    elif page > total_pages and total_pages > 0:
        page = total_pages
    
    # Calculate slice indices for current page
    start_idx = (page - 1) * results_per_page
    end_idx = start_idx + results_per_page
    
    # Get the portion of results for current page
    paginated_favorites = filtered_favorites[start_idx:end_idx]
    
    return render(request, 'pokemon/favorites.html', {
        'favorites': paginated_favorites,
        'query': query,
        'page': page,
        'total_pages': total_pages,
        'total_results': total_results,
        'all_favorites_count': len(all_favorite_pokemon)
    })

@login_required
def toggle_favorite(request, pokemon_id):
    """Add or remove a Pokémon from user's favorites."""
    if request.method != 'POST':
        return redirect('pokemon_details', name_or_id=pokemon_id)
    
    from .models import FavoritePokemon
    import json
    from django.http import JsonResponse
    
    # Check if the Pokémon exists
    pokemon_data = pokeapi.get_pokemon(pokemon_id)
    if not pokemon_data:
        if 'HTTP_X_REQUESTED_WITH' in request.META and request.META['HTTP_X_REQUESTED_WITH'] == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'error': 'Pokémon not found'})
        return redirect('pokemon_details', name_or_id=pokemon_id)
    
    # Check if the Pokémon is already in favorites
    favorite_exists = FavoritePokemon.objects.filter(
        user=request.user,
        pokemon_id=pokemon_id
    ).exists()
    
    if favorite_exists:
        # Remove from favorites
        FavoritePokemon.objects.filter(
            user=request.user,
            pokemon_id=pokemon_id
        ).delete()
        is_favorite = False
    else:
        # Add to favorites
        FavoritePokemon.objects.create(
            user=request.user,
            pokemon_id=pokemon_id,
            pokemon_name=pokemon_data['name']
        )
        is_favorite = True
    
    # If it's an AJAX request, return JSON
    if ('HTTP_X_REQUESTED_WITH' in request.META and request.META['HTTP_X_REQUESTED_WITH'] == 'XMLHttpRequest') or request.POST.get('is_ajax') == 'true':
        return JsonResponse({
            'success': True,
            'is_favorite': is_favorite,
            'pokemon_id': pokemon_id
        })
    
    # Otherwise, redirect back to the details page
    return redirect('pokemon_details', name_or_id=pokemon_id)

@login_required
def change_avatar(request):
    """Allow user to change their profile avatar."""
    if request.method == 'POST' and request.FILES.get('avatar'):
        profile = request.user.profile
        
        # Delete old avatar if exists (to save storage)
        if profile.avatar:
            profile.avatar.delete(save=False)
            
        profile.avatar = request.FILES['avatar']
        profile.save()
        messages.success(request, "Avatar updated successfully!")
        return redirect('profile')
        
    return render(request, 'account/change_avatar.html')
