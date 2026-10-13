//  drpy写源 模板规则说明 https://gitcode.net/supertlo/dr_py#%E6%A8%A1%E6%9D%BF%E8%A7%84%E5%88%99%E8%AF%B4%E6%98%8E
//  drpy写源 影片教程 http://101.34.67.237:5244/%E6%95%99%E8%82%B2/drpy
//  drpy写源 影片教程(m3u8切片) https://freedrpy.run.goorm.io/txt/jc/playlist.m3u8
// 海阔下载 https://haikuo.lanzoui.com/u/GoldRiver
// Pluto Player官方TG https://t.me/PlutoPlayer
// Pluto Player官方TG https://t.me/PlutoPlayerChannel

var rule = {
    title:'酷酷韩剧',
    host:'http://www.kan-tv.com',
    url:'/hanju/?p=fypage',
    searchUrl:'',
    searchable:0,
    quickSearch:0,
    class_name:'最新韩剧',
    class_url:'/',
    headers:{
        'User-Agent':'PC_UA'
    },
    timeout:5000,
    play_parse:true,
    lazy:'',
    limit:6,
    double:false,
    推荐:'*',
    一级:'.resource-main .shadow;h1&&Text;img&&src;.resource-abstract:eq(1)&&Text;a&&href',
    二级:{title:'h1&&Text;.article-detail-content&&Text',img:'img&&src',desc:'',content:'.article-detail-content&&Text',tabs:'.article-category-title',lists:'.article-category-list:eq(#id) a'},
    搜索:'',
}
