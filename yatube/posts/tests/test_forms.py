import shutil
import tempfile

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from posts.forms import PostForm
from posts.models import Comment, Group, Post

User = get_user_model()
TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostFormsTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='auth')
        cls.user_not_auth = User.objects.create_user(username='HasNoName')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
            description='Тестовое описание',
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовый пост',
            group=cls.group
        )
        cls.form = PostForm()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.guest_client = Client()
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user_not_auth)
        self.authorized_client_auth = Client()
        self.authorized_client_auth.force_login(self.user)

    def test_create_post(self):
        """Валидная форма создает новый пост."""
        posts_count = Post.objects.count()
        small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )
        uploaded = SimpleUploadedFile(
            name='small.gif',
            content=small_gif,
            content_type='image/gif'
        )
        form_data = {
            'text': 'Тестовый текст',
            'group': self.group.id,
            'image': uploaded,
        }
        responce = self.authorized_client.post(
            reverse('posts:post_create'),
            data=form_data,
            follow=True
        )
        self.assertRedirects(responce, reverse(
            'posts:profile', kwargs={'username': 'HasNoName'}))
        self.assertEqual(Post.objects.count(), posts_count + 1)
        new_post = Post.objects.get(id=2)
        self.assertEqual(new_post.text, form_data['text'])
        self.assertEqual(new_post.group.title, self.group.title)
        self.assertEqual(new_post.image, 'posts/small.gif')

    def test_post_edit(self):
        """Валидная форма редактирует существующий пост."""
        posts_count = Post.objects.count()
        form_data = {
            'text': 'Тестовый текст с редакцией',
            'group': '',
        }
        responce = self.authorized_client_auth.post(
            reverse('posts:post_edit', kwargs={'post_id': self.post.id}),
            data=form_data,
            follow=True
        )
        self.assertRedirects(responce, reverse(
            'posts:post_detail', kwargs={'post_id': self.post.id}))
        self.assertEqual(Post.objects.count(), posts_count)
        edit_post = Post.objects.get(id=1)
        self.assertEqual(edit_post.text, form_data['text'])
        self.assertEqual(edit_post.group, None)

    def test_label_text(self):
        """Тестирует метки label формы PostForm"""
        label_names = {
            'Текст': 'text',
            'Группа': 'group',
        }
        for text_label, label in label_names.items():
            with self.subTest(label=label):
                response = PostFormsTests.form.fields[label].label
                self.assertEqual(response, text_label)

    def test_help_text(self):
        """Тестирует тексты help_text формы PostForm"""
        help_text_names = {
            'Текст нового поста': 'text',
            'Группа, к которой будет относиться пост': 'group',
        }
        for text_help_text, help_text in help_text_names.items():
            with self.subTest(help_text=help_text):
                response = PostFormsTests.form.fields[help_text].help_text
                self.assertEqual(response, text_help_text)


class CommentFormsTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='auth')
        cls.user_not_auth = User.objects.create_user(username='HasNoName')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
            description='Тестовое описание',
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовый пост',
            group=cls.group
        )
        cls.comment = Comment.objects.create(
            post=cls.post,
            author=cls.user,
            text='Текст комментария',
        )

    def setUp(self):
        self.guest_client = Client()
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user_not_auth)
        self.authorized_client_auth = Client()
        self.authorized_client_auth.force_login(self.user)

    def test_add_comment(self):
        """Валидная форма создает новый комментарий."""
        comments_count = Comment.objects.count()
        form_data = {
            'text': 'Новый комментарий',
        }
        response = self.authorized_client.post(
            reverse('posts:add_comment', kwargs={'post_id': self.post.id}),
            data=form_data,
            follow=True
        )
        self.assertRedirects(response, reverse(
            'posts:post_detail', kwargs={'post_id': self.post.id}
        ))
        self.assertEqual(Comment.objects.count(), comments_count + 1)

    def test_add_comment_only_authorized_user(self):
        """Комментировать посты может только авторизованный пользователь."""
        comments_count = Comment.objects.count()
        form_data = {
            'text': 'Новый комментарий',
        }
        self.guest_client.post(
            reverse('posts:add_comment', kwargs={'post_id': self.post.id}),
            data=form_data,
            follow=True
        )
        self.assertEqual(Comment.objects.count(), comments_count)
