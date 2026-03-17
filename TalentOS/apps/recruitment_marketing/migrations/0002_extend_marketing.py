# Manually crafted migration for Feature 2 extended models.

import django.db.models.deletion
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('recruitment_marketing', '0001_initial'),
        ('jobs', '0006_workforce_planning_fields'),
        ('tenants', '0004_delete_subscription'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # ── EVPBlock ──────────────────────────────────────────────────────────
        migrations.CreateModel(
            name='EVPBlock',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('icon', models.CharField(blank=True, default='', help_text='Icon name or URL', max_length=100)),
                ('headline', models.CharField(max_length=255)),
                ('body', models.TextField(blank=True, default='')),
                ('display_order', models.IntegerField(default=0)),
                ('is_published', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('site', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='evp_blocks', to='recruitment_marketing.careersite')),
                ('tenant', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='evp_blocks', to='tenants.tenant')),
            ],
            options={'db_table': 'evp_blocks', 'ordering': ['site', 'display_order']},
        ),
        # ── EmployeeTestimonial ───────────────────────────────────────────────
        migrations.CreateModel(
            name='EmployeeTestimonial',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=200)),
                ('role', models.CharField(blank=True, default='', max_length=200)),
                ('department', models.CharField(blank=True, default='', max_length=200)),
                ('quote', models.TextField()),
                ('photo_url', models.URLField(blank=True, default='')),
                ('video_url', models.URLField(blank=True, default='')),
                ('is_featured', models.BooleanField(default=False)),
                ('display_order', models.IntegerField(default=0)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('site', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='testimonials', to='recruitment_marketing.careersite')),
                ('tenant', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='employee_testimonials', to='tenants.tenant')),
            ],
            options={'db_table': 'employee_testimonials', 'ordering': ['site', '-is_featured', 'display_order']},
        ),
        # ── RecruiterProfile ──────────────────────────────────────────────────
        migrations.CreateModel(
            name='RecruiterProfile',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('bio', models.TextField(blank=True, default='')),
                ('photo_url', models.URLField(blank=True, default='')),
                ('linkedin_url', models.URLField(blank=True, default='')),
                ('specialties', models.JSONField(blank=True, default=list, help_text='List of specialty strings')),
                ('is_public', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('tenant', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='recruiter_profiles', to='tenants.tenant')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='recruiter_profile', to=settings.AUTH_USER_MODEL)),
            ],
            options={'db_table': 'recruiter_profiles', 'unique_together': {('tenant', 'user')}},
        ),
        # ── DepartmentPage ────────────────────────────────────────────────────
        migrations.CreateModel(
            name='DepartmentPage',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=200)),
                ('slug', models.SlugField(max_length=100)),
                ('headline', models.CharField(blank=True, default='', max_length=255)),
                ('description', models.TextField(blank=True, default='')),
                ('hero_image_url', models.URLField(blank=True, default='')),
                ('open_roles_count', models.IntegerField(default=0)),
                ('is_published', models.BooleanField(default=False)),
                ('display_order', models.IntegerField(default=0)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('site', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='department_pages', to='recruitment_marketing.careersite')),
                ('tenant', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='department_pages', to='tenants.tenant')),
            ],
            options={
                'db_table': 'department_pages',
                'ordering': ['site', 'display_order'],
                'unique_together': {('site', 'slug')},
            },
        ),
        # ── OfficePage ────────────────────────────────────────────────────────
        migrations.CreateModel(
            name='OfficePage',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('city', models.CharField(max_length=200)),
                ('country', models.CharField(max_length=200)),
                ('address', models.CharField(blank=True, default='', max_length=500)),
                ('latitude', models.DecimalField(blank=True, decimal_places=6, max_digits=9, null=True)),
                ('longitude', models.DecimalField(blank=True, decimal_places=6, max_digits=9, null=True)),
                ('description', models.TextField(blank=True, default='')),
                ('photos', models.JSONField(blank=True, default=list, help_text='List of photo URLs')),
                ('perks', models.JSONField(blank=True, default=list, help_text='List of office-specific perks')),
                ('is_published', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('site', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='office_pages', to='recruitment_marketing.careersite')),
                ('tenant', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='office_pages', to='tenants.tenant')),
            ],
            options={'db_table': 'office_pages', 'ordering': ['site', 'country', 'city']},
        ),
        # ── JobDistributionChannel ────────────────────────────────────────────
        migrations.CreateModel(
            name='JobDistributionChannel',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=255)),
                ('channel_type', models.CharField(choices=[('job_board', 'Job Board'), ('social', 'Social Media'), ('aggregator', 'Aggregator'), ('university', 'University Portal'), ('diversity', 'Diversity Board'), ('internal', 'Internal Portal'), ('other', 'Other')], default='job_board', max_length=30)),
                ('is_active', models.BooleanField(default=True)),
                ('api_key', models.CharField(blank=True, default='', help_text='Encrypted at rest in production', max_length=500)),
                ('last_sync_at', models.DateTimeField(blank=True, null=True)),
                ('auto_post', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('tenant', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='job_distribution_channels', to='tenants.tenant')),
            ],
            options={'db_table': 'job_distribution_channels', 'ordering': ['name']},
        ),
        # ── JobDistributionPost ───────────────────────────────────────────────
        migrations.CreateModel(
            name='JobDistributionPost',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('external_id', models.CharField(blank=True, default='', help_text='ID on the external platform', max_length=255)),
                ('status', models.CharField(choices=[('pending', 'Pending'), ('posted', 'Posted'), ('failed', 'Failed'), ('removed', 'Removed'), ('expired', 'Expired')], default='pending', max_length=20)),
                ('posted_at', models.DateTimeField(blank=True, null=True)),
                ('cost', models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
                ('currency', models.CharField(default='USD', max_length=3)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('channel', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='posts', to='recruitment_marketing.jobdistributionchannel')),
                ('job', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='distribution_posts', to='jobs.job')),
                ('tenant', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='job_distribution_posts', to='tenants.tenant')),
            ],
            options={
                'db_table': 'job_distribution_posts',
                'ordering': ['-created_at'],
                'unique_together': {('job', 'channel')},
            },
        ),
        # ── MarketingCalendarEntry ────────────────────────────────────────────
        migrations.CreateModel(
            name='MarketingCalendarEntry',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('title', models.CharField(max_length=255)),
                ('entry_type', models.CharField(choices=[('social_post', 'Social Post'), ('campaign', 'Campaign'), ('event', 'Event'), ('job_launch', 'Job Launch'), ('content', 'Content'), ('email', 'Email'), ('other', 'Other')], default='other', max_length=30)),
                ('channel', models.CharField(blank=True, default='', max_length=100)),
                ('scheduled_date', models.DateField()),
                ('status', models.CharField(choices=[('planned', 'Planned'), ('in_progress', 'In Progress'), ('published', 'Published'), ('cancelled', 'Cancelled')], default='planned', max_length=20)),
                ('notes', models.TextField(blank=True, default='')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('created_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='marketing_calendar_entries', to=settings.AUTH_USER_MODEL)),
                ('linked_job', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='marketing_calendar_entries', to='jobs.job')),
                ('tenant', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='marketing_calendar_entries', to='tenants.tenant')),
            ],
            options={'db_table': 'marketing_calendar_entries', 'ordering': ['scheduled_date']},
        ),
        # ── BrandAnalyticsSnapshot ────────────────────────────────────────────
        migrations.CreateModel(
            name='BrandAnalyticsSnapshot',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('date', models.DateField()),
                ('career_site_views', models.IntegerField(default=0)),
                ('unique_visitors', models.IntegerField(default=0)),
                ('applications_started', models.IntegerField(default=0)),
                ('applications_completed', models.IntegerField(default=0)),
                ('top_source', models.CharField(blank=True, default='', max_length=255)),
                ('avg_time_on_site_seconds', models.IntegerField(default=0)),
                ('bounce_rate', models.DecimalField(decimal_places=2, default=0, max_digits=5)),
                ('site', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='analytics_snapshots', to='recruitment_marketing.careersite')),
                ('tenant', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='brand_analytics_snapshots', to='tenants.tenant')),
            ],
            options={
                'db_table': 'brand_analytics_snapshots',
                'ordering': ['-date'],
                'unique_together': {('site', 'date')},
            },
        ),
        # ── ChatbotFAQFlow ────────────────────────────────────────────────────
        migrations.CreateModel(
            name='ChatbotFAQFlow',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('trigger_keywords', models.JSONField(blank=True, default=list, help_text='List of trigger keyword strings')),
                ('response', models.TextField()),
                ('flow_type', models.CharField(choices=[('faq', 'FAQ Answer'), ('redirect', 'Redirect to Page'), ('apply', 'Prompt to Apply'), ('signup', 'Talent Community Signup'), ('contact', 'Contact Recruiter')], default='faq', max_length=20)),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('site', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='chatbot_flows', to='recruitment_marketing.careersite')),
                ('tenant', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='chatbot_faq_flows', to='tenants.tenant')),
            ],
            options={'db_table': 'chatbot_faq_flows', 'ordering': ['site']},
        ),
        # ── DayInLifeSection ──────────────────────────────────────────────────
        migrations.CreateModel(
            name='DayInLifeSection',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('department', models.CharField(blank=True, default='', max_length=200)),
                ('title', models.CharField(max_length=255)),
                ('media_url', models.URLField()),
                ('media_type', models.CharField(choices=[('image', 'Image'), ('video', 'Video')], default='image', max_length=10)),
                ('caption', models.TextField(blank=True, default='')),
                ('display_order', models.IntegerField(default=0)),
                ('is_published', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('site', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='day_in_life_sections', to='recruitment_marketing.careersite')),
                ('tenant', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='day_in_life_sections', to='tenants.tenant')),
            ],
            options={'db_table': 'day_in_life_sections', 'ordering': ['site', 'display_order']},
        ),
    ]
