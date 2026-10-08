let session=null,movies=[],categories=[];
const $=id=>document.getElementById(id);
const escapeHtml=value=>String(value??'').replace(/[&<>"']/g,ch=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]));
const palette=[['#3c5c9d','#16253f'],['#9a5a3e','#27171a'],['#6659a1','#211a35'],['#446f68','#162a2a'],['#985a7b','#301b29']];
async function request(url,opts={}){const r=await fetch(url,{credentials:'same-origin',...opts});const b=await r.json().catch(()=>({}));if(!r.ok)throw new Error(b.error||'REQUEST_FAILED');return b}
async function loadCatalog(){try{const d=await request('/api/catalog');session=d.user;movies=d.movies;categories=d.categories||[];render()}catch(e){session=null;$('login').hidden=false;$('app').hidden=true}}
function render(){
 $('login').hidden=true;$('app').hidden=false;
 $('role').textContent=session.role;
 $('hello').textContent=session.is_kids?'Perfil infantil: somente títulos Kids.':session.age<18?'Seu perfil é menor de 18: conteúdo adulto está bloqueado.':'Acesso completo ao catálogo liberado para esta conta.';
 $('movieCount').textContent=movies.length;
 $('catalogPanel').hidden=session.role!=='ADMIN';
 if(session.role==='ADMIN') renderAdminMovies();
 const cats=['all',...new Set(movies.map(m=>m.category))];
 $('filters').innerHTML=cats.map(c=>'<button type="button" data-cat="'+escapeHtml(c)+'">'+(c==='all'?'Todos':escapeHtml(c))+'</button>').join('');
 $('filters').onclick=e=>{const b=e.target.closest('button[data-cat]');if(b)show(b.dataset.cat)};
 show('all');
 if(['ADMIN','OPERATIONAL'].includes(session.role)){$('usersPanel').hidden=false;loadUsers()}else $('usersPanel').hidden=true;
}
function posterStyle(index){const p=palette[index%palette.length];return '--poster-a:'+p[0]+';--poster-b:'+p[1]}
function show(cat){
 document.querySelectorAll('#filters button').forEach(b=>b.classList.toggle('active',b.dataset.cat===cat));
 const list=cat==='all'?movies:movies.filter(m=>m.category===cat);
 $('movies').innerHTML=list.length?list.map((m,i)=>'<article class="movie-card"><div class="poster" style="'+posterStyle(i)+'"><div class="poster-top"><span class="badge">'+escapeHtml(m.category)+'</span><span class="rating">'+escapeHtml(m.rating)+'</span></div><span class="poster-letter">'+escapeHtml(m.title.slice(0,1))+'</span></div><div class="movie-body"><h3>'+escapeHtml(m.title)+'</h3><p>'+escapeHtml(m.description)+'</p><div class="movie-meta"><span>'+escapeHtml(m.year)+'</span><span>Disponível</span></div></div></article>').join(''):'<div class="empty-state">Nenhum título disponível nesta categoria.</div>';
}
function categoryName(slug){const c=categories.find(x=>x.slug===slug);return c?c.name:slug}
function renderAdminMovies(){
 $('adminMovies').innerHTML=movies.length?movies.map(m=>'<div class="user-row"><div class="user-main"><strong>'+escapeHtml(m.title)+'</strong><span>'+escapeHtml(categoryName(m.category))+' · '+escapeHtml(m.year)+' · '+escapeHtml(m.rating)+'</span></div><div class="row-actions"><button class="btn btn-ghost" type="button" data-edit-movie="'+escapeHtml(m.id)+'">Editar</button><button class="btn btn-ghost" type="button" data-delete-movie="'+escapeHtml(m.id)+'">Excluir</button></div></div>').join(''):'<div class="empty-state">Nenhum título cadastrado.</div>';
}
function fillMovieCategories(selected=''){ $('movieCategory').innerHTML=categories.map(c=>'<option value="'+escapeHtml(c.slug)+'">'+escapeHtml(c.name)+'</option>').join('');if(selected)$('movieCategory').value=selected; }
function openMovieDialog(movie=null){
 fillMovieCategories(movie?movie.category:categories[0]?.slug||'');
 $('movieId').value=movie?movie.id:'';$('movieTitle').value=movie?movie.title:'';$('movieYear').value=movie?movie.year:new Date().getFullYear();$('movieRating').value=movie?movie.rating:'L';$('movieDescription').value=movie?movie.description:'';$('movieFormMode').textContent=movie?'Edição':'Novo título';$('movieDialogTitle').textContent=movie?'Editar filme':'Adicionar filme';$('movieFormError').textContent='';$('movieDialog').showModal();
}
async function saveMovie(){
 const id=$('movieId').value;const payload={title:$('movieTitle').value.trim(),category:$('movieCategory').value,year:Number($('movieYear').value),rating:$('movieRating').value,description:$('movieDescription').value.trim()};
 try{await request(id?'/api/movies/'+id:'/api/movies',{method:id?'PATCH':'POST',headers:{'content-type':'application/json'},body:JSON.stringify(payload)});$('movieDialog').close();await loadCatalog()}catch(e){const msg={INVALID_TITLE:'Informe um título entre 1 e 100 caracteres.',CATEGORY_NOT_FOUND:'Categoria inválida.',INVALID_CATEGORY:'Categoria inválida.',INVALID_YEAR:'Ano inválido.',INVALID_RATING:'Classificação inválida.',INVALID_DESCRIPTION:'A descrição é obrigatória e deve ter até 500 caracteres.',MOVIE_NOT_FOUND:'Filme não encontrado.',CATALOG_ADMIN_ONLY:'Somente o ADMIN pode alterar o catálogo.'}[e.message]||e.message;$('movieFormError').textContent=msg}
}

async function loadUsers(){const d=await request('/api/users');$('users').innerHTML=d.users.map(u=>{const id=escapeHtml(u.id);const action=u.role==='ADMIN'?'':'<button class="btn btn-ghost" type="button" data-user="'+id+'" data-active="'+(!u.active)+'">'+(u.active?'Desativar':'Ativar')+'</button>';const del=session.role==='ADMIN'&&u.role!=='ADMIN'?'<button class="btn btn-ghost" type="button" data-delete-user="'+id+'">Excluir</button>':'';return '<div class="user-row"><div class="user-main"><strong>'+escapeHtml(u.username)+'</strong><span>'+escapeHtml(u.role)+' · '+escapeHtml(u.age)+' anos · '+(u.active?'ativo':'inativo')+'</span></div><div class="row-actions">'+action+del+'</div></div>'}).join('')}
$('loginForm').addEventListener('submit',async e=>{e.preventDefault();$('loginError').textContent='';try{await request('/api/auth/login',{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify({username:$('username').value.trim(),password:$('password').value})});await loadCatalog()}catch(e){$('loginError').textContent=e.message}});
$('logout').addEventListener('click',async()=>{await request('/api/auth/logout',{method:'POST'});await loadCatalog()});
$('users').addEventListener('click',async e=>{const b=e.target.closest('button[data-user]');if(b){await request('/api/users/'+b.dataset.user,{method:'PATCH',headers:{'content-type':'application/json'},body:JSON.stringify({active:b.dataset.active==='true'})});await loadCatalog();return}const d=e.target.closest('button[data-delete-user]');if(d){if(!confirm('Excluir este usuário?'))return;await request('/api/users/'+d.dataset.deleteUser,{method:'DELETE'});await loadCatalog()}});
$('addUser').addEventListener('click',async()=>{const username=prompt('Usuário (3–30 caracteres: letras, números, ., _ ou -)');if(!username)return;const password=prompt('Senha temporária (8–128 caracteres)');if(!password)return;const age=Number(prompt('Idade (0–120)',18));if(!Number.isInteger(age)||age<0||age>120){alert('Idade inválida. Informe um número inteiro entre 0 e 120.');return}try{await request('/api/users',{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify({username,age,active:true,password})});await loadCatalog()}catch(e){alert(({INVALID_USERNAME:'Usuário inválido.',INVALID_PASSWORD:'A senha deve ter entre 8 e 128 caracteres.',INVALID_AGE:'Idade inválida.',USERNAME_EXISTS:'Esse usuário já existe.',INVALID_ACTIVE:'Status inválido.'}[e.message]||e.message))}});
$('addMovie').addEventListener('click',()=>openMovieDialog());
$('closeMovieDialog').addEventListener('click',()=>$('movieDialog').close());
$('movieForm').addEventListener('submit',async e=>{e.preventDefault();await saveMovie()});
$('adminMovies').addEventListener('click',async e=>{const edit=e.target.closest('button[data-edit-movie]');if(edit){const movie=movies.find(m=>m.id===edit.dataset.editMovie);if(movie)openMovieDialog(movie);return}const del=e.target.closest('button[data-delete-movie]');if(del){const movie=movies.find(m=>m.id===del.dataset.deleteMovie);if(!movie||!confirm('Excluir o filme “'+movie.title+'”?'))return;try{await request('/api/movies/'+movie.id,{method:'DELETE'});await loadCatalog()}catch(err){alert(err.message)}}});
loadCatalog();