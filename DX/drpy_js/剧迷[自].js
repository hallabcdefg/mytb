var rule = {
    模板: '自动',
    title: '剧迷[自动]',
    host: 'https://www.jagcys.com/',
    url: '/vodshow/fyclass/page/fypage.html',
    searchUrl: '/vodsearch**/page/fypage.html',
    class_parse: '.navbar-items&&li:gt(1):lt(8);a&&Text;a&&href;/vodtype/(.*?)\.html',
    cate_exclude: '今日更新|热榜',
}