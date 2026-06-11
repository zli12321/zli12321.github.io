document.querySelectorAll('[data-github-repo]').forEach(el => {
    const repo = el.getAttribute('data-github-repo');
    const cacheKey = `githubStars:${repo}`;
    const cached = localStorage.getItem(cacheKey);

    const render = (stars) => {
        el.innerHTML = `<i class="fas fa-star"></i> ${parseInt(stars).toLocaleString()}`;
    };

    if (cached) {
        const { stars, timestamp } = JSON.parse(cached);
        if (Date.now() - timestamp < 6 * 60 * 60 * 1000) {
            render(stars);
            return;
        }
    }

    fetch(`https://api.github.com/repos/${repo}`)
        .then(r => r.json())
        .then(data => {
            if (data.stargazers_count !== undefined) {
                localStorage.setItem(cacheKey, JSON.stringify({ stars: data.stargazers_count, timestamp: Date.now() }));
                render(data.stargazers_count);
            }
        })
        .catch(() => {});
});
