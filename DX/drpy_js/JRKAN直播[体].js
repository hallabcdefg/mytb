
var rule = {
    title: 'JRKAN直播',
    host: 'http://www.jrkankan.com/?lan=1',
    // JRKAN备用域名:www.jrkankan.com / www.jrkan365.com / jrsyyds.com / www.jryyds.com / jrskan.com / jrsbxj.com
    // JRKAN网址发布:qiumi1314.com
    url: '/fyclass',
    searchUrl: '',
    searchable: 0,
    quickSearch: 0,
    class_name: '全部',
    class_url: '/',
    //class_url:'?live',
    headers: {
        'User-Agent': 'MOBILE_UA'
    },
    timeout: 5000,
    play_parse: true,
    lazy: $js.toString(() => {
        let _id = input.match(/id=(.*?)&/)[1];
        _id = decodeURIComponent(_id);
        let html = request(input);
        // log(html);
        let src = html.match(/src='(.*?)'/)[1].replace('"+id1+"', _id);
        log('src:' + src);
        //let _url = `http://play.sportsteam356.com/play/${_id}.html`;
        let _url = urljoin(input, src);
        log('_url:' + _url);
        html = request(_url);
        _url = 'http:' + pdfh(html, 'iframe&&src');
        log('iframe_url:' + _url);

        function J_get(name, url) {
            url = url ? url : 'http://cloud.yumixiu768.com/player/msss.html?id=/live/705782/playlist.m3u8?k=f8444f76c5852ada0b6ac9181714b310&t=1819702363';
            var start = url.indexOf(name + '=');
            if (start == -1) return '';
            var len = start + name.length + 1;
            var end = url.indexOf('######', len);
            if (end == -1) end = url.length;
            return unescape(url.substring(len, end));
        }

        let id = J_get('id', _url);
        if (id) {
            let purl = "//hls.szsummer.cn" + id;
            if (!purl.startsWith('http')) {
                purl = 'https:' + purl;
            }
            log('play_url:' + purl);
            input = {parse: 0, url: purl};
        }
    }),
    limit: 6,
    double: false,
    推荐: '*',
    一级: $js.toString(() => {
        let d = [];
        let html = request(input);
        let tabs = pdfa(html, 'ul.d-touch');
        tabs.forEach((it) => {
            let ps = pdfh(it, '.name&&Text');
            let pz = pdfh(it, '.name:eq(1)&&Text');
            let pk = pdfh(it, '.name:eq(2)&&Text');
            let img = pd(it, 'img&&src');
            let timer = pdfh(it, '.lab_time&&Text');
            let url = pd(it, 'a.me&&href');
            d.push({
                title: pz + '🆚' + pk,
                desc: timer + '🏆' + ps,
                img: img,
                url: url
            });
        });
        setResult(d);
    }),
    二级: {
        "title": ".sub_list li:lt(2)&&Text;.sub_list li:eq(0)&&Text",
        "img": "img&&src",
        "desc": ";;;.lab_team_home&&Text;.lab_team_away&&Text",
        "content": ".sub_list ul&&Text",
        "tabs": "js:TABS=['JRKAN直播']",
        lists: $js.toString(() => {
            //log(TABS);
            LISTS = [];
            let html = request(input);
            let data = pdfa(html, '.sub_playlist&&a');
            let lists1 = [];
            data.forEach((it) => {
                let name = pdfh(it, 'strong&&Text');
                let url1 = pdfh(it, 'a&&data-play');
                // log(url1);
                if (url1.length > 8) { //过滤无效选集
                    let url = pd(it, 'a&&data-play', input);
                    lists1.push(name + '$' + url);
                }
            });
            LISTS.push(lists1);
        }),
    },
    搜索: '',
}