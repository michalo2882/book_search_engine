new Vue({
    el: '#app',
    data: {
        currentRoute: window.location.pathname,
        searchField: '',
        loading: false,
        items: [],
        noResults: false
    },
    methods: {
        async search() {
            if (this.searchField) {
                this.loading = true;
                this.noResults = false;
                let resp = await fetch(`/api/v1/search?query=${this.searchField}`);
                if (resp.ok) {
                    let data = await resp.json();
                    this.items = data.items;
                }
                this.noResults = !this.items.length;
                this.loading = false;
            }
        },
        async submit(e) {
            e.preventDefault();
        }
    }
});
