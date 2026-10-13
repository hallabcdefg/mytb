var rule = {
    模板: '自动',
    title: '电影先生[自动]',
    host: 'https://www.zgcwt.com',
    url: '/vodshow/fyclass/page/fypage.html',
    class_parse: '.grid-items&&li:lt(6);a&&Text;a&&href;.*/(.*?).html',
    searchUrl: '/vodsearch**/page/fypage.html',
    搜索: '.module-items .module-search-item;h3&&a&&Text;img&&data-src;.video-serial&&Text;h3&&a&&href',
}




