from rest_framework import viewsets
from rest_framework import status
from rest_framework.exceptions import NotAuthenticated
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.decorators import action

from apps.blog.access_policy import PostAccessPolicy, LikeAccessPolicy
from apps.blog.serializers import PostSerializer, LikeSerializer
from apps.blog.permissions import IsOwner
from apps.blog.models import Post, Like


class PostViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows users to be viewed or edited.
    """

    queryset = Post.objects.all()
    serializer_class = PostSerializer
    permission_classes = [PostAccessPolicy]

    def get_queryset(self):
        user = self.request.user
        if user.is_authenticated:
            return self.queryset.get_posts_include_unpablished(user)
        return self.queryset.published()

    def create(self, request):
        composition = Post.objects.create(**request.data, user=request.user)
        composition.save()
        serializer_context = {"request": request}
        serializer = PostSerializer(composition, context=serializer_context)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], permission_classes=[IsAuthenticated])
    def like(self, request, pk=None):
        post = Post.objects.get(pk=pk)
        self.reaction(post, request.user, reaction=True)
        return Response({"status": "Post liked."})

    @action(detail=True, methods=["post"], permission_classes=[IsAuthenticated])
    def unlike(self, request, pk=None):
        post = Post.objects.get(pk=pk)
        self.reaction(post, request.user, reaction=False)
        return Response({"status": "Post unliked."})

    def reaction(self, post, user, *, reaction: bool) -> Like:
        like = Like.objects.filter(post=post, user=user).first()
        if like is None:
            like = Like.objects.create(post=post, user=user, like=reaction)
        else:
            like.like = reaction
            like.save()
        return like

    @action(detail=True, methods=["post"], permission_classes=[IsAuthenticated])
    def delete_reaction(self, request, pk=None):
        post = Post.objects.get(pk=pk)
        like = Like.objects.get(post=post, user=request.user)
        like.delete()
        return Response({"status": "User reaction deleted."})


class LikeViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows users to be viewed or edited.
    """

    queryset = Like.objects.all()
    serializer_class = LikeSerializer
    permission_classes = [LikeAccessPolicy, IsOwner]

    def get_queryset(self):
        """
        This view should return a list of all the likes
        for the currently authenticated user.
        """
        params = {}
        if self.request.user.is_anonymous:
            raise NotAuthenticated("You must login for get this data!")
        params["user"] = self.request.user

        if self.request.query_params.get("post"):
            params["post__id"] = self.request.query_params.get("post")

        return self.queryset.filter(**params)
