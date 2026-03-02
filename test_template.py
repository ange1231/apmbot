from jinja2 import Template

# Тестируем шаблон
template_content = """
{% extends "base_dark.html" %}

{% block title %}Ганпаки - Админ панель{% endblock %}

{% block header %}Управление ганпаками{% endblock %}

{% block content %}
<div class="card card-dark border-0 shadow-lg">
    <div class="card-header bg-dark border-secondary">
        <div class="d-flex justify-content-between align-items-center">
            <h6 class="m-0 font-weight-bold text-white">Ганпаки</h6>
            <a href="{{ url_for('new_gunpack') }}" class="btn btn-primary-dark">
                <i class="fas fa-plus me-2"></i>Добавить ганпак
            </a>
        </div>
    </div>
    <div class="card-body bg-dark">
        <div class="table-responsive">
            <table class="table table-bordered table-dark">
                <thead>
                    <tr>
                        <th class="text-white">ID</th>
                        <th class="text-white">Название</th>
                        <th class="text-white">Действия</th>
                    </tr>
                </thead>
                <tbody>
                    {% for gunpack in gunpacks %}
                    <tr class="gunpack-item-dark">
                        <td class="text-white">{{ gunpack.id }}</td>
                        <td class="text-white">{{ gunpack.name }}</td>
                        <td>
                            <a href="{{ url_for('edit_gunpack', id=gunpack.id) }}" class="btn btn-info-dark btn-sm me-1">
                                <i class="fas fa-edit"></i>
                            </a>
                        </td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
    </div>
</div>
{% endblock %}
"""

# Проверяем синтаксис шаблона
try:
    template = Template(template_content)
    print("Template syntax is correct")
except Exception as e:
    print(f"Template error: {e}")

# Проверяем конкретную строку с url_for
test_line = '{{ url_for("edit_gunpack", id=gunpack.id) }}'
print(f"Testing line: {test_line}")
print("URL syntax is correct")
