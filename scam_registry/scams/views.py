from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .models import Article
from .forms import ArticleForm
import datetime

def home(request):
    articles = Article.objects.order_by('-pub_date')[:10]
    return render(request, 'scams/home.html', {'articles': articles})

@login_required
def article_new(request):
    if request.method == "POST":
        form = ArticleForm(request.POST)
        if form.is_valid():
            article = form.save(commit=False)
            article.pub_date = datetime.datetime.now()
            article.save()
            return redirect('home')
    else:
        form = ArticleForm()
    return render(request, 'scams/article_edit.html', {'form': form})
