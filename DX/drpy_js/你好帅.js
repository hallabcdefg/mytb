var rule = {
    title: '你好帅影院',
    host: 'https://nhsyy.com',
    url: '/vodshow/fyclass--------fypage---.html',
    searchUrl: '/vodsearch/**----------fypage---.html',
    searchable: 2, //是否启用全局搜索,
    quickSearch: 0, //是否启用快速搜索,
    filterable: 0, //是否启用分类筛选,
    class_parse: '.nav-menu-items&&li;a&&Text;a&&href;.*/(.*?).html',
    play_parse: true,
    lazy: `js:
        var html = JSON.parse(request(input).match(/r player_.*?=(.*?)</)[1]);
        var url = html.url;
        if (html.encrypt == '1') {
            url = unescape(url)
        } else if (html.encrypt == '2') {
            url = unescape(base64Decode(url))
        }
        if (/\\.m3u8|\\.mp4/.test(url)) {
            input = {
                jx: 0,
                url: url,
                parse: 0
            }
        } else {
            input
        }
    `,
    limit: 6,
    推荐: '.module-list;.module-items&&.module-item;a&&title;img&&data-src;.module-item-text&&Text;a&&href',
    double: true, // 推荐内容是否双层定位
    一级: '.module-items .module-item;a&&title;img&&data-src;.module-item-text&&Text;a&&href',
    二级: {
        "title": "h1&&Text;.tag-link&&Text",
        "img": ".module-item-pic&&img&&data-src",
        "desc": ".video-info-items:eq(0)&&Text;.video-info-items:eq(1)&&Text;.video-info-items:eq(2)&&Text;.video-info-items:eq(3)&&Text",
        "content": ".vod_content&&Text",
        "tabs": ".module-tab-item",
        "lists": ".module-player-list:eq(#id)&&.scroll-content&&a"
    },
    搜索: '.module-items .module-search-item;img&&alt;img&&data-src;.video-serial&&Text;a&&href',
}