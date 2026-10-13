var rule = {
  模板:'自动',
  模板修改: $js.toString(() => {
        Object.assign(muban.自动.二级, {
            tabs: '.nav.nav-tabs a',
        });
    }),
  title:'奇趣影院',
  host:'https://www.qqutv.com',
  url:'/qiqu/fyclass/page/fypage.html',
  //class_parse: '.navbar-items li:gt(1):lt(8);a&&Text;a&&href;/vodtype/(.*?)/',
  searchUrl: 'https://www.qqutv.com/so**/page/fypage.html',
}