// Main JavaScript entrypoint for Q&A Platform

/**
 * Register Alpine.js voteWidget component
 */
function registerVoteWidget() {
    if (typeof Alpine !== 'undefined') {
        Alpine.data('voteWidget', ({ action, upvotes, downvotes, userVote, isComment = false }) => ({
            action,
            upvotes: Number(upvotes),
            downvotes: Number(downvotes),
            userVote: userVote !== null && userVote !== undefined ? Number(userVote) : null,
            loading: false,

            get isUpvoted() {
                return this.userVote === 1;
            },

            get isDownvoted() {
                return this.userVote === -1;
            },

            get upvoteClasses() {
                if (this.isUpvoted) {
                    return 'bg-rose-50 border-rose-300 text-rose-600 font-semibold';
                }
                return isComment
                    ? 'bg-white border-gray-200 text-gray-600 hover:bg-gray-50 hover:border-gray-300'
                    : 'bg-white border-gray-300 text-gray-700 hover:bg-gray-50 hover:border-gray-400';
            },

            get downvoteClasses() {
                if (this.isDownvoted) {
                    return 'bg-gray-800 border-gray-800 text-white font-semibold';
                }
                return isComment
                    ? 'bg-white border-gray-200 text-gray-500 hover:bg-gray-50 hover:border-gray-300 hover:text-gray-900'
                    : 'bg-white border-gray-300 text-gray-600 hover:bg-gray-50 hover:border-gray-400 hover:text-gray-900';
            },

            async vote(value) {
                if (this.loading) return;
                this.loading = true;

                try {
                    const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value;
                    const response = await fetch(this.action, {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/x-www-form-urlencoded',
                            'X-Requested-With': 'XMLHttpRequest',
                            'Accept': 'application/json',
                            ...(csrfToken ? { 'X-CSRFToken': csrfToken } : {})
                        },
                        body: new URLSearchParams({
                            value: String(value),
                            ...(csrfToken ? { csrfmiddlewaretoken: csrfToken } : {})
                        })
                    });

                    if (response.status === 401) {
                        const data = await response.json();
                        if (data.login_url) {
                            window.location.href = data.login_url;
                            return;
                        }
                    }

                    if (!response.ok) {
                        throw new Error(`HTTP error ${response.status}`);
                    }

                    const data = await response.json();
                    this.userVote = data.user_vote;
                    this.upvotes = data.upvotes_count;
                    this.downvotes = data.downvotes_count;
                } catch (err) {
                    console.error('Error submitting vote:', err);
                } finally {
                    this.loading = false;
                }
            }
        }));
    }
}

document.addEventListener('alpine:init', registerVoteWidget);
if (typeof Alpine !== 'undefined') {
    registerVoteWidget();
}
