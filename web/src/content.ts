export type Modality = 'text' | 'audio' | 'visual';
export type Item = { id: string; concept: string; stem: string; options: string[]; answer: number; objective: string };
export type Concept = { id: string; word: string; number: number; row: number; col: number; direction: 'across' | 'down'; clue: string; text: string; alt: string };
// Technical demonstration content v1; pending teacher validation. Clues deliberately avoid definitions.
export const concepts: Concept[] = [
 {id:'root',word:'ROOT',number:1,row:0,col:2,direction:'down',clue:'A four-letter plant word. It rhymes with “boot”.',text:'Roots hold many plants in the soil. They take in water and minerals from the soil, helping the plant grow.',alt:'A plant with branching roots below the soil. Arrows show water moving from soil into the roots.'},
 {id:'moss',word:'MOSS',number:2,row:1,col:1,direction:'across',clue:'A four-letter plant word. It rhymes with “boss”.',text:'Moss is a small plant without flowers. It often grows in damp, shady places and takes in water through its surface.',alt:'Small moss plants form a green mat on a damp rock under shade. Water droplets reach the surface.'},
 {id:'stem',word:'STEM',number:3,row:3,col:1,direction:'across',clue:'A four-letter plant word. It rhymes with “gem”.',text:'A stem supports a plant’s leaves and flowers. It carries water from the roots to other parts of the plant.',alt:'A plant with its stem highlighted between roots and leaves. Upward arrows show water travelling through the stem.'},
];
const item = (concept: string, phase: string, n: number, stem: string, options: string[], answer: number, objective: string): Item => ({id:`${concept}-${phase}-${n}-v1`,concept,stem,options,answer,objective});
export const baseline: Item[] = [
 item('root','pre',1,'Which part of many plants takes in water from the soil?',['Flower','Root','Leaf'],1,'recognition'),
 item('root','pre',2,'A plant stays firmly in the soil on a windy day. Which part helps it stay in place?',['Petal','Fruit','Root'],2,'application'),
 item('moss','pre',1,'Which description best fits moss?',['A small plant without flowers','A tall flowering tree','A type of animal'],0,'recognition'),
 item('moss','pre',2,'Where would you most likely find moss growing?',['A dry, sunny desert','A damp, shady rock','Inside a hot oven'],1,'application'),
 item('stem','pre',1,'Which part supports the leaves of a plant?',['Seed','Root hair','Stem'],2,'recognition'),
 item('stem','pre',2,'Water moves from roots towards leaves. Which part carries it between them?',['Stem','Petal','Fruit'],0,'application'),
];
export const post: Item[] = [
 item('root','post',1,'What is one job of a plant’s roots?',['Making petals colourful','Taking in water and minerals','Producing sunlight'],1,'recognition'),
 item('root','post',2,'A seedling has damaged roots. What may become more difficult?',['Absorbing water from soil','Seeing other plants','Making the soil brighter'],0,'application'),
 item('moss','post',1,'How does moss take in water?',['Only through flowers','Through its surface','Through a woody trunk'],1,'recognition'),
 item('moss','post',2,'A gardener wants a suitable place for moss. Which spot should they choose?',['A dry windowsill in full sun','A hot, dry path','A moist rock under a tree'],2,'application'),
 item('stem','post',1,'Which statement describes a stem?',['It supports leaves and carries water','It is always below the soil','It only makes seeds'],0,'recognition'),
 item('stem','post',2,'A flower has roots in water. How does water reach the flower above?',['Through the surrounding air only','Through its stem','Through its petals first'],1,'application'),
];
export const CONTENT_VERSION = 'science-demo-v1';
