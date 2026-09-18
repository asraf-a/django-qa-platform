// Main JavaScript entrypoint for Q&A Platform

(function () {
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initVoteHandlers);
    } else {
        initVoteHandlers();
    }
})();

/**
 * Initializes AJAX voting for question, answer, and comment vote forms.
 * Intercepts both button clicks and form submissions to completely prevent page reload.
 */
function initVoteHandlers() {
    // 1. Intercept click directly on the submit button or SVG/span inside it
    document.addEventListener('click', async (event) => {
        const button = event.target.closest('button');
        if (!button) return;

        const form = button.closest('form');
        if (!form) return;

        const action = form.getAttribute('action') || form.action;
        if (!action || !action.includes('/vote/')) return;

        event.preventDefault();
        event.stopPropagation();

        await handleVote(form);
    });

    // 2. Intercept submit event as a safeguard
    document.addEventListener('submit', async (event) => {
        const form = event.target.tagName === 'FORM' ? event.target : event.target.closest('form');
        if (!form) return;

        const action = form.getAttribute('action') || form.action;
        if (!action || !action.includes('/vote/')) return;

        event.preventDefault();
        event.stopPropagation();

        await handleVote(form);
    });
}

/**
 * Performs asynchronous vote request and updates the UI.
 */
async function handleVote(form) {
    if (form.dataset.voting === 'true') {
        return;
    }
    form.dataset.voting = 'true';

    const voteContainer = form.parentElement;
    if (!voteContainer) {
        form.dataset.voting = 'false';
        return;
    }

    const upvoteForm = voteContainer.querySelector('input[name="value"][value="1"]')?.closest('form');
    const downvoteForm = voteContainer.querySelector('input[name="value"][value="-1"]')?.closest('form');

    const upvoteBtn = upvoteForm?.querySelector('button');
    const downvoteBtn = downvoteForm?.querySelector('button');

    // Prevent duplicate clicks while in flight
    if (upvoteBtn) upvoteBtn.disabled = true;
    if (downvoteBtn) downvoteBtn.disabled = true;

    try {
        const action = form.getAttribute('action') || form.action;
        const formData = new FormData(form);
        const csrfToken = formData.get('csrfmiddlewaretoken');

        const response = await fetch(action, {
            method: 'POST',
            body: formData,
            headers: {
                'X-Requested-With': 'XMLHttpRequest',
                'Accept': 'application/json',
                ...(csrfToken ? { 'X-CSRFToken': csrfToken } : {})
            }
        });

        if (response.status === 401) {
            const data = await response.json();
            if (data.login_url) {
                window.location.href = data.login_url;
                return;
            }
        }

        if (!response.ok) {
            throw new Error(`Vote request failed with status: ${response.status}`);
        }

        const data = await response.json();
        updateVoteUI({
            voteContainer,
            form,
            upvoteBtn,
            downvoteBtn,
            data
        });
    } catch (error) {
        console.error('Error submitting vote:', error);
    } finally {
        if (upvoteBtn) upvoteBtn.disabled = false;
        if (downvoteBtn) downvoteBtn.disabled = false;
        form.dataset.voting = 'false';
    }
}

/**
 * Updates button states, counts, icons, and badges based on the JSON response.
 */
function updateVoteUI({ voteContainer, form, upvoteBtn, downvoteBtn, data }) {
    const isUpvoted = data.user_vote === 1;
    const isDownvoted = data.user_vote === -1;

    // Determine icon size based on existing button markup
    const existingSvg = (upvoteBtn || downvoteBtn)?.querySelector('svg');
    const isSmall = existingSvg && existingSvg.classList.contains('w-3.5');
    const iconSize = isSmall ? 'w-3.5 h-3.5' : 'w-4 h-4';
    const isComment = isSmall;

    // 1. Update Upvote Button
    if (upvoteBtn) {
        upvoteBtn.setAttribute('aria-pressed', isUpvoted ? 'true' : 'false');

        if (isUpvoted) {
            upvoteBtn.classList.remove('bg-white', 'text-gray-700', 'text-gray-600', 'border-gray-200', 'border-gray-300', 'hover:bg-gray-50', 'hover:border-gray-300', 'hover:border-gray-400');
            upvoteBtn.classList.add('bg-rose-50', 'border-rose-300', 'text-rose-600', 'font-semibold');
            upvoteBtn.innerHTML = `
                <svg class="${iconSize} text-rose-600 shrink-0" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
                    <path d="M2 10.5a1.5 1.5 0 113 0v6a1.5 1.5 0 01-3 0v-6zM6 10.333v5.43a2 2 0 001.106 1.79l.05.025A4 4 0 008.943 18h5.416a2 2 0 001.962-1.608l1.2-6A2 2 0 0015.56 8H12V4a2 2 0 00-2-2 1 1 0 00-1 1v.667a4 4 0 01-.8 2.4L6.8 7.933a4 4 0 00-.8 2.4z" />
                </svg>
                <span>${data.upvotes_count}</span>
            `;
        } else {
            upvoteBtn.classList.remove('bg-rose-50', 'border-rose-300', 'text-rose-600', 'font-semibold');
            const defaultBorder = isComment ? 'border-gray-200' : 'border-gray-300';
            const defaultText = isComment ? 'text-gray-600' : 'text-gray-700';
            const defaultHoverBorder = isComment ? 'hover:border-gray-300' : 'hover:border-gray-400';
            upvoteBtn.classList.add('bg-white', defaultBorder, defaultText, 'hover:bg-gray-50', defaultHoverBorder);
            upvoteBtn.innerHTML = `
                <svg class="${iconSize} text-gray-400 shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
                    <path stroke-linecap="round" stroke-linejoin="round" d="M14 10h4.764a2 2 0 011.789 2.894l-3.5 7A2 2 0 0115.263 21h-4.017c-.163 0-.326-.02-.485-.06L7 20m7-10V5a2 2 0 00-2-2h-.095c-.5 0-.905.405-.905.905 0 .714-.211 1.412-.608 2.006L7 11v9m7-10h-2M7 20H5a2 2 0 01-2-2v-6a2 2 0 012-2h2.5" />
                </svg>
                <span>${data.upvotes_count}</span>
            `;
        }
    }

    // 2. Update Downvote Button
    if (downvoteBtn) {
        downvoteBtn.setAttribute('aria-pressed', isDownvoted ? 'true' : 'false');

        if (isDownvoted) {
            downvoteBtn.classList.remove('bg-white', 'text-gray-600', 'text-gray-500', 'border-gray-200', 'border-gray-300', 'hover:bg-gray-50', 'hover:border-gray-300', 'hover:border-gray-400', 'hover:text-gray-900');
            downvoteBtn.classList.add('bg-gray-800', 'border-gray-800', 'text-white', 'font-semibold');
            downvoteBtn.innerHTML = `
                <svg class="${iconSize} text-white shrink-0" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
                    <path d="M18 9.5a1.5 1.5 0 11-3 0v-6a1.5 1.5 0 013 0v6zM14 9.667v-5.43a2 2 0 00-1.106-1.79l-.05-.025A4 4 0 0011.057 2H5.64a2 2 0 00-1.962 1.608l-1.2 6A2 2 0 004.44 12H8v4a2 2 0 002 2 1 1 0 001-1v-.667a4 4 0 01.8-2.4l1.4-1.866a4 4 0 00.8-2.4z" />
                </svg>
                <span>${data.downvotes_count}</span>
            `;
        } else {
            downvoteBtn.classList.remove('bg-gray-800', 'border-gray-800', 'text-white', 'font-semibold');
            const defaultBorder = isComment ? 'border-gray-200' : 'border-gray-300';
            const defaultText = isComment ? 'text-gray-500' : 'text-gray-600';
            const defaultHoverBorder = isComment ? 'hover:border-gray-300' : 'hover:border-gray-400';
            downvoteBtn.classList.add('bg-white', defaultBorder, defaultText, 'hover:bg-gray-50', defaultHoverBorder, 'hover:text-gray-900');
            downvoteBtn.innerHTML = `
                <svg class="${iconSize} text-gray-400 shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
                    <path stroke-linecap="round" stroke-linejoin="round" d="M10 14H5.236a2 2 0 01-1.789-2.894l3.5-7A2 2 0 018.736 3h4.018a2 2 0 01.485.06l3.76 1.06m-7 10v5a2 2 0 002 2h.096c.5 0 .905-.405.905-.904 0-.715.211-1.413.608-2.008L17 13V4m-7 10h2m5-10h2a2 2 0 012 2v6a2 2 0 01-2 2h-2.5" />
                </svg>
                <span>${data.downvotes_count}</span>
            `;
        }
    }

    // 3. Update nearby badge/pill count if present
    const badge = voteContainer.querySelector('span.rounded-full') ||
                  voteContainer.parentElement?.querySelector('span.rounded-full') ||
                  form.closest('article')?.querySelector('span.rounded-full');
    if (badge && badge.textContent.includes('vote')) {
        const plural = data.upvotes_count === 1 ? 'vote' : 'votes';
        badge.textContent = `${data.upvotes_count} ${plural}`;
        if (data.upvotes_count > 0) {
            badge.classList.remove('bg-gray-100', 'text-gray-600');
            badge.classList.add('bg-rose-50', 'text-rose-700', 'border', 'border-rose-100');
        } else {
            badge.classList.remove('bg-rose-50', 'text-rose-700', 'border', 'border-rose-100');
            badge.classList.add('bg-gray-100', 'text-gray-600');
        }
    }
}
