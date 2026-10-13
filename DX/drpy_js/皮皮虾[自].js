var rule = {
  模板:'自动',
  模板修改: $js.toString(() => {
        muban.自动.二级.tabs = '.module-tab-item.tab-item';
    }),
  title:'皮皮虾[自动]',
  host:'http://www.ppxyes.com',
  url:'/s/fyclass/page/fypage.html',
  class_parse: '.navbar-items li:gt(1):lt(8);a&&Text;a&&href;/(\\d+).html',
   searchUrl: '/vodsearch**/page/fypage.html',
   }