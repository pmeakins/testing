from django.urls import path
from . import views
urlpatterns = [
    path('', views.base, name='base'),
]



from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
import json

def test_form(request):
    """Render the test form page"""
    return render(request, 'v1/test_form.html')

def ajax_echo(request):
    """Process AJAX request and echo back the input"""
    if request.method == 'POST':
        if request.content_type == 'application/json':
            data = json.loads(request.body)
            input_value = data.get('message', '')
        else:
            input_value = request.POST.get('message', '')

        # Process your data here (you can add any logic)
        response_data = {
            'success': True,
            'message': f'You entered: {input_value}',
            'original_input': input_value
        }
        return JsonResponse(response_data)

    return JsonResponse({'success': False, 'error': 'Invalid request'})
