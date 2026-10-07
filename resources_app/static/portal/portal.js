document.addEventListener('DOMContentLoaded', () => {
    const searchInput = document.getElementById('courseSearchInput');
    const courseResults = document.getElementById('courseResults');
    const resultCount = document.getElementById('courseResultsCount');
    let searchTimer;
    let activeRequest;

    const makeElement = (tag, className, text) => {
        const element = document.createElement(tag);
        if (className) element.className = className;
        if (text) element.textContent = text;
        return element;
    };

    if (searchInput && courseResults && resultCount) {
        const renderCourses = (courses) => {
            courseResults.replaceChildren();
            resultCount.textContent = `${courses.length} course${courses.length === 1 ? '' : 's'} found`;

            if (!courses.length) {
                const empty = makeElement('div', 'empty-state');
                empty.append(
                    makeElement('h2', '', 'No courses found'),
                    makeElement('p', '', 'Try another search, or check back for newly published courses.')
                );
                courseResults.append(empty);
                return;
            }

            const authenticated = document.body.dataset.authenticated === 'true';
            const csrfToken = document.querySelector('meta[name="csrf-token"]').content;

            courses.forEach((course) => {
                const card = makeElement('article', 'course-card');
                card.append(
                    makeElement('div', 'course-tag', course.code),
                    makeElement('h2', '', course.title),
                    makeElement('p', '', course.description),
                    makeElement('p', '', `Instructor: ${course.instructor}`),
                    makeElement(
                        'p',
                        'course-instructor',
                        course.learner_count
                            ? `${course.learner_count} learner${course.learner_count === 1 ? '' : 's'} enrolled`
                            : 'Be the first to enroll'
                    )
                );

                const footer = makeElement('div', 'card-footer');
                footer.append(makeElement('span', '', `${course.duration_weeks} weeks`));
                if (authenticated) {
                    const form = document.createElement('form');
                    form.method = 'post';
                    form.action = course.enrollment_url;
                    const csrf = document.createElement('input');
                    csrf.type = 'hidden';
                    csrf.name = 'csrfmiddlewaretoken';
                    csrf.value = csrfToken;
                    form.append(csrf);
                    const enroll = makeElement('button', 'text-button', 'Enroll');
                    enroll.type = 'submit';
                    form.append(enroll);
                    footer.append(form);
                } else {
                    const loginLink = makeElement('a', '', 'Log in to enroll');
                    loginLink.href = '/accounts/login/?next=/courses/';
                    footer.append(loginLink);
                }
                card.append(footer);
                courseResults.append(card);
            });
        };

        searchInput.addEventListener('input', () => {
            window.clearTimeout(searchTimer);
            searchTimer = window.setTimeout(async () => {
                if (activeRequest) activeRequest.abort();
                activeRequest = new AbortController();
                const url = new URL(courseResults.dataset.catalogUrl, window.location.origin);
                url.searchParams.set('format', 'json');
                url.searchParams.set('q', searchInput.value.trim());

                try {
                    const response = await fetch(url, {
                        headers: { Accept: 'application/json' },
                        signal: activeRequest.signal
                    });
                    if (!response.ok) throw new Error(`Course search failed (${response.status}).`);
                    const data = await response.json();
                    renderCourses(data.courses);
                } catch (error) {
                    if (error.name === 'AbortError') return;
                    resultCount.textContent = error.message;
                }
            }, 180);
        });
    }

    const registrationForm = document.getElementById('registrationForm');
    if (registrationForm) {
        const feedback = document.getElementById('registrationFeedback');
        const password = registrationForm.elements.password1;
        const confirmation = registrationForm.elements.password2;
        const validateForm = () => {
            confirmation.setCustomValidity(
                password.value && confirmation.value && password.value !== confirmation.value
                    ? 'Passwords do not match.'
                    : ''
            );

            const invalid = registrationForm.querySelector(':invalid');
            registrationForm.querySelectorAll('input').forEach((input) => {
                input.setAttribute('aria-invalid', String(!input.checkValidity()));
            });
            feedback.textContent = invalid
                ? invalid.validationMessage || 'Please complete this field.'
                : '';
            return !invalid;
        };

        registrationForm.addEventListener('input', validateForm);
        registrationForm.addEventListener('submit', (event) => {
            if (!validateForm()) {
                event.preventDefault();
                registrationForm.querySelector(':invalid')?.focus();
            }
        });
    }

    document.querySelectorAll('.alert-message').forEach((alert) => {
        window.setTimeout(() => {
            alert.style.opacity = '0';
            window.setTimeout(() => alert.remove(), 450);
        }, 4000);
    });
});
