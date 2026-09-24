import { ComponentFixture, TestBed } from '@angular/core/testing';

import { PresencaPanelComponent } from './presenca-panel.component';

describe('PresencaPanelComponent', () => {
  let component: PresencaPanelComponent;
  let fixture: ComponentFixture<PresencaPanelComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      declarations: [ PresencaPanelComponent ]
    })
    .compileComponents();
  });

  beforeEach(() => {
    fixture = TestBed.createComponent(PresencaPanelComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
