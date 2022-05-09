import random

from django.db.models import Count
from django.views.generic import CreateView, DetailView, ListView
from mixins import CustomLoginRequiredMixin

from . import forms, models
from .models import Note
from .forms import CommentForm
from django.shortcuts import render, get_object_or_404


class NoteCreateView(CustomLoginRequiredMixin, CreateView):
    """ This view will handle the creation of notes, and saving them to the database """

    template_name = "notes/create.html"
    form_class = forms.CreateNoteForm

    def form_valid(self, form, *args, **kwargs):
        user = self.request.user
        note = form.save(commit=False)
        note.writer = user
        note.save()
        return super().form_valid(form, *args, **kwargs)


class NotesListView(ListView):
    """ This view will handle displaying all the notes in the database """

    # model = models.Note
    paginate_by = 10
    template_name = "notes/list.html"

    def get_queryset(self, *args, **kwargs):
        return (
            models.Note.objects.annotate(count=Count("bookmark__id"))
            .order_by("-count")
            .filter(hidden=False, draft=False)
        )
        # return sorted(qs, key=lambda x: random.random())


# class NotesDetailView(DetailView):
#     """ This view will handle displaying the notes from the database """

#     model = models.Note
#     template_name = "notes/detail.html"

#     def get_context_data(self, *args, **kwargs):
#         context = super().get_context_data(*args, **kwargs)
#         note = context["object"]
#         context["comments"] = models.Comment.objects.filter(note=note, active=True)
#         context["bookmarks"] = models.Bookmark.objects.filter(note=note).count()
#         return context

# def note_detail(request, slug):
#     template_name = 'notes/detail.html'
#     note = get_object_or_404(note, slug=slug)
#     comments = note.comments.filter(note=note, active=True)
#     #bookmarks = Note.bookmarks.filter(note=note).count()
#     new_comment = None
#     # Comment posted
#     if request.method == 'POST':
#         comment_form = CommentForm(data=request.POST)
#         if comment_form.is_valid():

#             # Create Comment object but don't save to database yet
#             new_comment = comment_form.save(commit=False)
#             # Assign the current post to the comment
#             new_comment.note = note
#             # Save the comment to the database
#             new_comment.save()
#     else:
#         comment_form = CommentForm()

#     return render(request, template_name, {'note': note,
#                                            'comments': comments,
#                                            #'bookmarks': bookmarks,
#                                            'new_comment': new_comment,
#                                            'comment_form': comment_form})


def NoteDetail(request,pk):
    post = get_object_or_404(Note, pk=pk)
    comments=models.Comment.objects.filter(note=note)
    if request.method == "POST":
        comment_form = CommentForm(request.POST or None)
        if comment_form.is_valid():
            comment=comment_form.save(commit=False)
            comment.note=note
            comment.save()
    else:
        comment_form = CommentForm()
    context={
        'note':note,
        'comments':comments,
        'comment_form':comment_form,
    }
    return render(request, 'notes/detail.html', context)

class PrivateListView(ListView):
    """ This view will handle displaying of private notes of the user. """

    paginate_by = 10
    queryset = models.Note.objects.filter(hidden=True).order_by("-updated_at")
    template_name = "notes/private.html"


class PublicListView(ListView):
    """ This view will handle displaying of publicly available notes """

    paginate_by = 10
    queryset = models.Note.objects.filter(hidden=False).order_by("-updated_at")
    template_name = "notes/public.html"


class DraftListView(ListView):
    """ This view will handle displaying draft notes """

    paginate_by = 10
    queryset = models.Note.objects.filter(draft=True).order_by("-updated_at")
    template_name = "notes/drafts.html"


class BookmarkListView(CustomLoginRequiredMixin, ListView):
    """ This view will handle display of bookmarks """

    paginate_by = 10
    template_name = "notes/bookmarks.html"

    def get_queryset(self, *args, **kwargs):
        bookmarks = models.Bookmark.objects.filter(user=self.request.user)
        return [bookmark.note for bookmark in bookmarks]