import shutil
import tempfile
import time

from django import forms
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.core.cache import cache

from ..models import Group, Post, Follow

User = get_user_model()
TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostViewsTests(TestCase):
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
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовый пост',
            group=cls.group,
            image=uploaded,
        )

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

    def test_pages_uses_correct_template(self):
        """View-функция использует соответствующий шаблон."""
        templates_pages_names = {
            reverse('posts:index'): 'posts/index.html',
            reverse('posts:group_posts', kwargs={'slug': 'test-slug'}):
            'posts/group_list.html',
            reverse('posts:profile', kwargs={'username': 'HasNoName'}):
            'posts/profile.html',
            reverse('posts:post_detail', kwargs={'post_id': self.post.id}):
            'posts/post_detail.html',
            reverse('posts:post_edit', kwargs={'post_id': self.post.id}):
            'posts/create_post.html',
            reverse('posts:post_create'): 'posts/create_post.html',
            reverse('posts:follow_index'): 'posts/follow.html',
        }
        for reverse_name, template in templates_pages_names.items():
            with self.subTest(reverse_name=reverse_name):
                response = self.authorized_client_auth.get(reverse_name)
                self.assertTemplateUsed(response, template)

    def test_index_page_show_correct_context(self):
        """Шаблон index сформирован с правильным подтекстом."""
        response = self.authorized_client.get(reverse('posts:index'))
        first_object = response.context['page_obj'][0]
        post_text_0 = first_object.text
        post_author_0 = first_object.author
        post_group_0 = first_object.group
        post_image_0 = first_object.image
        self.assertEqual(post_text_0, 'Тестовый пост')
        self.assertEqual(post_author_0.username, 'auth')
        self.assertEqual(post_group_0.title, 'Тестовая группа')
        self.assertEqual(post_image_0, 'posts/small.gif')

    def test_group_list_page_show_correct_context(self):
        """Шаблон group_list сформирован с правильным подтекстом."""
        response = self.authorized_client.get(reverse(
            'posts:group_posts', kwargs={'slug': 'test-slug'}))
        first_object = response.context['page_obj'][0]
        post_text_0 = first_object.text
        post_author_0 = first_object.author
        post_group_0 = first_object.group
        post_slug_0 = first_object.group.slug
        post_image_0 = first_object.image
        self.assertEqual(post_text_0, 'Тестовый пост')
        self.assertEqual(post_author_0.username, 'auth')
        self.assertEqual(post_group_0.title, 'Тестовая группа')
        self.assertEqual(post_slug_0, 'test-slug')
        self.assertEqual(post_image_0, 'posts/small.gif')

    def test_profile_page_show_correct_context(self):
        """Шаблон profile сформирован с правильным подтекстом."""
        response = self.authorized_client.get(reverse(
            'posts:profile', kwargs={'username': 'auth'}))
        first_object = response.context['page_obj'][0]
        post_text_0 = first_object.text
        post_author_0 = first_object.author
        post_group_0 = first_object.group
        post_image_0 = first_object.image
        self.assertEqual(post_text_0, 'Тестовый пост')
        self.assertEqual(post_author_0.username, 'auth')
        self.assertEqual(post_group_0.title, 'Тестовая группа')
        self.assertEqual(post_image_0, 'posts/small.gif')

    def test_post_detail_page_show_correct_context(self):
        """Шаблон post_detail сформирован с правильным подтекстом."""
        response = self.authorized_client.get(reverse(
            'posts:post_detail', kwargs={'post_id': self.post.id}))
        self.assertEqual(response.context.get('post').text, 'Тестовый пост')
        self.assertEqual(response.context.get('post').author.username, 'auth')
        self.assertEqual(
            response.context.get('post').group.title, 'Тестовая группа'
        )
        self.assertEqual(response.context.get('post').image, 'posts/small.gif')

    def test_post_create_page_show_correct_context(self):
        """Шаблон post_create сформирован с правильным подтекстом."""
        response = self.authorized_client.get(reverse('posts:post_create'))
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.fields.ChoiceField,
        }
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context.get('form').fields.get(value)
                self.assertIsInstance(form_field, expected)

    def test_post_edit_page_show_correct_context(self):
        """Шаблон post_edit сформирован с правильным подтекстом."""
        response = self.authorized_client_auth.get(reverse(
            'posts:post_edit', kwargs={'post_id': self.post.id}))
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.fields.ChoiceField,
        }
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context.get('form').fields.get(value)
                self.assertIsInstance(form_field, expected)

    def test_cache_index(self):
        """Проверка кэширования для index."""
        response = self.authorized_client.get(reverse('posts:index'))
        posts = response.content
        Post.objects.create(
            author=self.user,
            text='Тестовый пост для кэша',
        )
        response_new = self.authorized_client.get(reverse('posts:index'))
        new_posts = response_new.content
        self.assertEqual(new_posts, posts)
        cache.clear()
        response_clear = self.authorized_client.get(reverse('posts:index'))
        posts_clear = response_clear.content
        self.assertNotEqual(posts_clear, posts)

    def test_profile_follow_and_unfollow_correct(self):
        """Проверка возможности подписываться на других пользователей
        и удалять их из подписок"""
        cache.clear()
        self.authorized_client.get(reverse(
            'posts:profile_follow', kwargs={'username': self.user}))
        self.assertTrue(Follow.objects.filter(
            user=self.user_not_auth, author=self.user).exists())
        self.authorized_client.get(reverse(
            'posts:profile_unfollow', kwargs={'username': self.user}))
        self.assertFalse(Follow.objects.filter(
            user=self.user_not_auth, author=self.user).exists())

    def test_new_post_appears_followers(self):
        """Проверка: Новая запись пользователя появляется в ленте тех,
        кто на него подписан и не появляется в ленте тех, кто не подписан."""
        user_other = User.objects.create_user(username='Other')
        self.authorized_client_other = Client()
        self.authorized_client_other.force_login(user_other)
        self.authorized_client.get(reverse(
            'posts:profile_follow', kwargs={'username': self.user}))
        post_new = Post.objects.create(
            author=self.user,
            text='Тестовый пост для подписчиков',
        )
        response = self.authorized_client.get(reverse('posts:follow_index'))
        posts_authorized_client = response.context['page_obj']
        response = self.authorized_client_other.get(reverse(
            'posts:follow_index'))
        posts_authorized_client_other = response.context['page_obj']
        self.assertIn(
            post_new, posts_authorized_client
        )
        self.assertNotIn(
            post_new, posts_authorized_client_other
        )


class PaginatorViewsTest(TestCase):
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
        cls.other_group = Group.objects.create(
            title='Тестовая группа 2',
            slug='test-slug_2',
            description='Тестовое описание',
        )
        cls.post = {}
        for i in range(13):
            cls.post[i] = Post.objects.create(
                author=cls.user,
                text=(f'Тестовый пост {i}'),
                group=cls.group,
            )
            time.sleep(0.1)
        cls.post_without_group = Post.objects.create(
            author=cls.user,
            text='Тестовый пост в другой',
            group=cls.other_group,
        )
        cache.clear()

    def setUp(self):
        self.guest_client = Client()
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user_not_auth)
        self.authorized_client_auth = Client()
        self.authorized_client_auth.force_login(self.user)

    def test_first_page_index_contains_ten_posts(self):
        """Проверка: количество постов на первой странице index равно 10"""
        response = self.guest_client.get(reverse('posts:index'))
        self.assertEqual(len(response.context['page_obj']), 10)

    def test_second_page_index_contains_four_posts(self):
        """Проверка: на второй странице index должно быть четыре поста"""
        response = self.guest_client.get(reverse('posts:index') + '?page=2')
        self.assertEqual(len(response.context['page_obj']), 4)

    def test_first_page_group_list_contains_ten_posts(self):
        """
        Проверка: количество постов на первой странице group_list равно 10
        """
        response = self.guest_client.get(reverse(
            'posts:group_posts', kwargs={'slug': 'test-slug'}))
        self.assertEqual(len(response.context['page_obj']), 10)

    def test_second_page_group_list_contains_four_posts(self):
        """Проверка: на второй странице group_list должно быть четыре поста"""
        response = self.guest_client.get(reverse(
            'posts:group_posts', kwargs={'slug': 'test-slug'}) + '?page=2')
        self.assertEqual(len(response.context['page_obj']), 3)

    def test_first_page_profile_contains_ten_posts(self):
        """Проверка: количество постов на первой странице profile равно 10"""
        response = self.guest_client.get(reverse(
            'posts:profile', kwargs={'username': 'auth'}))
        self.assertEqual(len(response.context['page_obj']), 10)

    def test_second_page_profile_contains_four_posts(self):
        """Проверка: на второй странице profile должно быть четыре поста"""
        response = self.guest_client.get(reverse(
            'posts:profile', kwargs={'username': 'auth'}) + '?page=2')
        self.assertEqual(len(response.context['page_obj']), 4)

    def test_post_on_index(self):
        """Проверка: созданный пост есть на главной странице."""
        response = self.authorized_client.get(reverse('posts:index'))
        self.assertIn(Post.objects.get(id=14), response.context['page_obj'])

    def test_post_on_index(self):
        """Проверка: созданный пост есть на странице группы."""
        response = self.authorized_client.get(reverse(
            'posts:group_posts', kwargs={'slug': 'test-slug'}))
        self.assertIn(Post.objects.get(id=10), response.context['page_obj'])

    def test_post_on_index(self):
        """Проверка: созданный пост есть в профайле пользователя."""
        response = self.authorized_client.get(reverse(
            'posts:profile', kwargs={'username': 'auth'}))
        self.assertIn(Post.objects.get(id=10), response.context['page_obj'])

    def test_post_on_index(self):
        """Проверка: созданный пост в группе 2 отсутствует в группе 1."""
        response = self.authorized_client.get(reverse(
            'posts:group_posts', kwargs={'slug': 'test-slug'}))
        self.assertNotIn(Post.objects.get(id=14), response.context['page_obj'])
