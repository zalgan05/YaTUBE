from http import HTTPStatus

from django.contrib.auth import get_user_model
from django.test import Client, TestCase

from ..models import Group, Post

User = get_user_model()


class PostURLTests(TestCase):
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
        )

    def setUp(self):
        self.guest_client = Client()
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user_not_auth)
        self.authorized_client_auth = Client()
        self.authorized_client_auth.force_login(self.user)

    def test_urls_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        templates_url_names = {
            '/': 'posts/index.html',
            f'/group/{self.group.slug}/': 'posts/group_list.html',
            '/profile/auth/': 'posts/profile.html',
            f'/posts/{self.post.id}/': 'posts/post_detail.html',
            f'/posts/{self.post.id}/edit/': 'posts/create_post.html',
            '/create/': 'posts/create_post.html',
            '/unexisting_page/': 'core/404.html',
            '/follow/': 'posts/follow.html',
        }
        for address, template in templates_url_names.items():
            with self.subTest(address=address):
                response = self.authorized_client_auth.get(address)
                self.assertTemplateUsed(response, template)

    def test_urls_exists_at_desired_location_guest_client(self):
        """Страница доступна любому пользователю."""
        code_status_urls = {
            HTTPStatus.OK.value: '/',
            HTTPStatus.OK.value: '/group/test-slug/',
            HTTPStatus.OK.value: '/profile/HasNoName/',
            HTTPStatus.OK.value: '/posts/1/',
            HTTPStatus.NOT_FOUND.value: '/unexisting_page/',
        }
        for code_status, address in code_status_urls.items():
            with self.subTest(address=address):
                response = self.guest_client.get(address)
                self.assertEqual(response.status_code, code_status)

    def test_urls_exists_at_desired_location_authorized_client(self):
        """Страница доступна авторизованному пользователю."""
        code_status_urls = {
            HTTPStatus.OK.value: '/create/',
        }
        for code_status, address in code_status_urls.items():
            with self.subTest(address=address):
                response = self.authorized_client.get(address)
                self.assertEqual(response.status_code, code_status)

    def test_post_edit_url_exists_at_desired_location_author(self):
        """Страница /posts/1/edit/ доступна автору."""
        response = self.authorized_client_auth.get('/posts/1/edit/')
        self.assertEqual(response.status_code, HTTPStatus.OK.value)

    def test_urls_redirect_anonymous_on_login(self):
        """Страница перенаправит анонимного
        пользователя на страницу логина.
        """
        redirect_pages_names = {
            '/auth/login/?next=/create/': '/create/',
            f'/auth/login/?next=/posts/{self.post.id}/edit/':
            f'/posts/{self.post.id}/edit/',
            f'/auth/login/?next=/posts/{self.post.id}/comment/':
            f'/posts/{self.post.id}/comment/'
        }
        for redirect, url in redirect_pages_names.items():
            with self.subTest(url=url):
                response = self.guest_client.get(url, follow=True)
                self.assertRedirects(response, redirect)
