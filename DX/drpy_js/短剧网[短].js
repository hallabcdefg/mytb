var rule = {
    title: '短剧网',
    host: 'http://2ju.cc/show/duanju',
    url: '/fyclass/page/fypage.html',
    searchUrl:'/vodsearch/wd/**/page/fypage.html',
    class_name:'全部&女频&男频',
    class_url:'show/duanju&label/boy/file/girl&label/boy/file/boy',
    class_parse:'.type_aside&&a[href*=show];a&&Text;a&&href;(show.*).html',
    play_parse:true,
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
    推荐: '*',
    double: true,
    一级: '.img-list&&li;a&&title;img&&data-original;;a&&href',
    二级: {
    title: 'h1&&Text',
    img: 'img&&src',
    desc: '.info&&dl:eq(0)&&Text;.info&&dl:eq(1)&&Text;.info&&dl:eq(2)&&Text;',
    content: '.content-cols&&Text',
    tabs: '',
    lists: '#play_tab_box&&a',
    tab_text: '线路',
  },
    搜索: '*',
}