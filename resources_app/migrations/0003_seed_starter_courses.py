from django.db import migrations


STARTER_COURSES = (
    (
        'WEB101',
        'Full-Stack Web Development',
        'Build responsive websites with HTML, CSS and JavaScript, then create database-backed web applications with Python and Django. Includes practical projects and deployment fundamentals.',
        12,
    ),
    (
        'PYT101',
        'Python Programming',
        'Learn Python from the ground up: data types, control flow, functions, object-oriented programming, files and APIs. Finish with a portfolio-ready application.',
        8,
    ),
    (
        'UIX101',
        'UI/UX Design Fundamentals',
        'Practice user research, information architecture, wireframing and prototyping. Create accessible interface designs and test them with real users.',
        8,
    ),
    (
        'DBA101',
        'Database Design and SQL',
        'Design relational databases, write SQL queries and work with joins, indexes and transactions. Apply your skills to a practical business data project.',
        6,
    ),
    (
        'CYB101',
        'Cybersecurity Essentials',
        'Explore security principles, common threats, safe network practices, access control and incident response through guided defensive lab exercises.',
        8,
    ),
    (
        'DSA101',
        'Data Analytics with Excel and Power BI',
        'Clean and analyze data, build useful visualizations and communicate findings with Excel and Power BI. Work through a complete reporting case study.',
        8,
    ),
)


def add_starter_courses(apps, schema_editor):
    Course = apps.get_model('resources_app', 'Course')
    database = schema_editor.connection.alias
    for code, title, description, duration_weeks in STARTER_COURSES:
        Course.objects.using(database).get_or_create(
            code=code,
            defaults={
                'title': title,
                'description': description,
                'duration_weeks': duration_weeks,
            },
        )


class Migration(migrations.Migration):
    dependencies = [
        ('resources_app', '0002_course_studentprofile_enrollment'),
    ]

    operations = [
        migrations.RunPython(add_starter_courses, migrations.RunPython.noop),
    ]
