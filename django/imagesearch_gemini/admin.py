from django.contrib import admin
from django.utils.html import format_html
from django.conf import settings
from .models import ImageEmbedding, SearchQuery


@admin.register(ImageEmbedding)
class ImageEmbeddingAdmin(admin.ModelAdmin):
    def image_thumbnail(self, obj):
        if obj.image_path:
            # 외부 URL이면 그대로, 아니면 MEDIA_URL 기준으로 경로 생성
            if obj.image_path.startswith("http://") or obj.image_path.startswith(
                "https://"
            ):
                url = obj.image_path
            else:
                # image_path가 'images/...' 등 상대경로라면 MEDIA_URL + image_path
                rel_path = obj.image_path.lstrip("/")
                url = (
                    settings.MEDIA_URL + rel_path
                    if not rel_path.startswith(settings.MEDIA_URL.lstrip("/"))
                    else rel_path
                )
            return format_html(
                '<img src="{}" style="max-height:100px; max-width:150px;" />',
                url,
            )
        return ""

    image_thumbnail.short_description = "미리보기"

    def tag_list(self, obj):
        return ", ".join([t.name for t in obj.tags.all()])

    tag_list.short_description = "태그"

    list_display = (
        "image_thumbnail",
        "date_taken",
        "city_from_gps",
        "location_user",
        "tag_list",
        "updated_at",
    )
    search_fields = ("image_path", "image_unique_id", "location_user")
    list_filter = ("date_taken_exif", "date_taken_user", "created_at")
    readonly_fields = ("created_at", "updated_at")


@admin.register(SearchQuery)
class SearchQueryAdmin(admin.ModelAdmin):
    list_display = ("query_text", "searched_at")
    search_fields = ("query_text",)
    readonly_fields = ("searched_at",)
