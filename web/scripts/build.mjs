import {mkdir,readFile,writeFile,copyFile} from 'node:fs/promises';
import {stripTypeScriptTypes} from 'node:module';
await mkdir('dist',{recursive:true});
for(const name of ['content','engine']) {
 const ts=await readFile(`src/${name}.ts`,'utf8');
 await writeFile(`dist/${name}.js`,stripTypeScriptTypes(ts).replaceAll('./content.ts','./content.js'));
}
for(const [from,to] of [['index.html','index.html'],['src/app.js','app.js'],['src/styles.css','styles.css']])await copyFile(from,`dist/${to}`);
console.log('Built dependency-free CrossLearn demo in web/dist.');
