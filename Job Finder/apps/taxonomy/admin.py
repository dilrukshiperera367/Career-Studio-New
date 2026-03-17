"""Taxonomy admin registrations."""
from django.contrib import admin
from .models import Province, District, JobCategory, JobSubCategory, Industry, Skill, EducationLevel


@admin.register(Province)
class ProvinceAdmin(admin.ModelAdmin):
    list_display = ("name_en", "name_si", "name_ta", "slug")
    search_fields = ("name_en",)


@admin.register(District)
class DistrictAdmin(admin.ModelAdmin):
    list_display = ("name_en", "province", "slug")
    list_filter = ("province",)
    search_fields = ("name_en",)


class JobSubCategoryInline(admin.TabularInline):
    model = JobSubCategory
    extra = 0


@admin.register(JobCategory)
class JobCategoryAdmin(admin.ModelAdmin):
    list_display = ("name_en", "slug", "icon", "is_featured", "sort_order")
    list_filter = ("is_featured",)
    search_fields = ("name_en",)
    prepopulated_fields = {"slug": ("name_en",)}
    inlines = [JobSubCategoryInline]


@admin.register(JobSubCategory)
class JobSubCategoryAdmin(admin.ModelAdmin):
    list_display = ("name_en", "category", "slug")
    list_filter = ("category",)
    search_fields = ("name_en",)
    prepopulated_fields = {"slug": ("name_en",)}


@admin.register(Industry)
class IndustryAdmin(admin.ModelAdmin):
    list_display = ("name_en", "slug", "naics_code", "is_active")
    search_fields = ("name_en",)
    prepopulated_fields = {"slug": ("name_en",)}


@admin.register(Skill)
class SkillAdmin(admin.ModelAdmin):
    list_display = ("name_en", "slug", "category")
    list_filter = ("category",)
    search_fields = ("name_en",)
    prepopulated_fields = {"slug": ("name_en",)}


@admin.register(EducationLevel)
class EducationLevelAdmin(admin.ModelAdmin):
    list_display = ("name_en", "sort_order")
